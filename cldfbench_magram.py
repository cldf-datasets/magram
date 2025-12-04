import pathlib
import re
import unicodedata
from collections import defaultdict
from itertools import chain, zip_longest
from string import Template

from clldutils.misc import slug
from cldfbench import Dataset as BaseDataset, CLDFSpec
from simplepybtex.database import BibliographyData, parse_file

# file maker do be like that sometimes...
COLUMN_MAP = {
    'f1_Code':                 'Code',
    'f2_Subset':               'Subset',
    'f3_Datasource':           'Data_Source',
    'f4_Authors':              'Author(s)',
    'f5_MAreaD':               'Macro-Area_Dryer',
    'f6_MAreaH':               'Macro-Area_Hammarström_Donohue',
    'f7_Family':               'Family',
    'f8_Glottocode':           'Glottocode',
    'f9_ISO':                  'ISO 639-3',
    'f10_Genus':               'Genus',
    'f11_Languagename':        'Language',
    'f12':                     'level_of_reconstruction_if_applicable',
    'f13_Source_form':         'Source:Form',
    'f14_Source_meaning':      'Source:Meaning',
    'f15_Source_meaning_simp': 'Source:Meaning_simplified',
    'f16_Source_Labelgroup':   'Source:Label_Group',
    'f17_Target_form':         'Target:Form',
    'f18_Target_meaning':      'Target:Meaning',
    'f19_Target_meaning_simp': 'Target:Meaning_simplified',
    'f20_Target_Labelgroup':   'Target:Label_Group',
    'f21_Ex':                  'Example:Material',
    'f22_Ex_gloss':            'Example:Glossing',
    'f23_Ex_translation':      'Example:Translation',
    'Example_Bibkeys':         'Example_Bibkeys',
    'f24_Ex_reference':        'Example:Reference',
    'f25':                     'Comments',
    'f26':                     'value:semantic_integrity',
    'f27':                     'value:phonetic_reduction',
    'f28':                     'value:paradigmaticity',
    'f29':                     'value:bondedness',
    'f30':                     'value:paradigmatic_variability',
    'f31':                     'value:syntagmatic_variability',
    'f32':                     'value:decategorization',
    'f33':                     'value:allomorphy',
    'f34':                     'change:semantic_integrity',
    'f35':                     'change:phonetic_reduction',
    'f36':                     'change:paradigmaticity',
    'f37':                     'change:bondedness',
    'f38':                     'change:paradigmatic_variability',
    'f39':                     'change:syntagmatic_variability',
    'f40':                     'change:decategorization',
    'f41':                     'change:allomorphy',
}


ASCII_DIAGRAM = """\
             Starting point:
       written text by contributors
           (Handbook & SL30)

                   |
                   v

     Coding (data, metadata, evaluation)
      from text by MAGRAM team *coders*
    using questionnaire & *team* meetings

                   |
                   v

         Improving coding (*team*) <-------.
                                           |
                   |                    Feedback
                   v                       |
                                           |
         sending coding sheets to  --------´
              *contributors*

                   |
                   v

     Formatting, streamlining glossing
           & grammatical labels
              (*MAGRAM team*)

                   |
                   v

      Roll-out of MAGRAM version 1.0
"""


def parse_raw_data(raw_data):
    return [
        {new_k: trimmed_v
         for k, v in row.items()
         if (new_k := COLUMN_MAP.get(k)) and (trimmed_v := v.strip())}
        for row in raw_data]


def parse_ccodes(csv_rows):
    return {
        (row['Parameter_ID'], row['Original_Name']):
        {k: trimmed_v for k, v in row.items() if (trimmed_v := v.strip())}
        for row in csv_rows}


def get_languoids(glottolog, rows):
    all_glottocodes = {gc for row in rows if (gc := row.get('Glottocode'))}
    return {
        lg.id: lg
        for lg in glottolog.languoids(ids=all_glottocodes)}


def make_row_id(row):
    return '{}-{}-{}-{}'.format(
        row['Code'],
        slug(row['Source:Form']),
        slug(row['Target:Form']),
        slug(row['Target:Meaning_simplified']))


def make_language_id(row):
    return slug(row['Language'])


def make_contrib_id(row):
    return slug(row['Subset'])


def get_languoid(languoids, row):
    if (glottocode := row.get('Glottocode')):
        if (languoid := languoids.get(glottocode)):
            return languoid
        else:
            print('Language {}: invalid glottocode: {}'.format(
                row['Language'], glottocode))
            return None
    else:
        return None


def make_languages(raw_data, languoids):
    languages = {}
    for row in raw_data:
        if (language_id := make_language_id(row)) not in languages:
            language = {
                'ID': language_id,
                'Name': row['Language'],
            }
            if (languoid := get_languoid(languoids, row)):
                language['Glottocode'] = languoid.id
                language['ISO639P3code'] = languoid.iso or ''
                language['Latitude'] = languoid.latitude or ''
                language['Longitude'] = languoid.longitude or ''
                if languoid.macroareas:
                    language['Macroarea'] = languoid.macroareas[0].name
            elif language['Name'] == 'Quechua II':
                # TODO(johannes): coordinates
                language['Family'] = 'quec1387'
            languages[language_id] = language
    return languages


def make_contributions(raw_data):
    contributions = {}
    for row in raw_data:
        if (contrib_id := make_contrib_id(row)) not in contributions:
            contributions[contrib_id] = {
                'ID': contrib_id,
                'Name': row['Subset'],
            }
    return contributions


def make_concepts(raw_data):
    concepts = {}
    for row in raw_data:
        target_id = slug(row['Target:Meaning_simplified'])
        if target_id not in concepts:
            concepts[target_id] = {
                'ID': target_id,
                'Name': row['Target:Meaning_simplified'],
            }
        source_id = slug(row['Source:Meaning_simplified'])
        if source_id not in concepts:
            concepts[source_id] = {
                'ID': source_id,
                'Name': row['Source:Meaning_simplified'],
            }
    return concepts


def visual_len(s):
    return sum(1 for c in s if unicodedata.category(c) not in {'Mn', 'Me', 'Cf'})


def visual_pad(s, new_width):
    vl = visual_len(s)
    return '{}{}'.format(s, ' ' * (new_width - vl)) if new_width > vl else s


def aligned_example(analysed, gloss, indent=0):
    widths = [
        max(visual_len(a), visual_len(g))
        for a, g in zip_longest(analysed, gloss, fillvalue='')]
    prefix = ' ' * indent if indent else ''
    line1 = '  '.join(visual_pad(a, w) for a, w in zip(analysed, widths))
    line2 = '  '.join(visual_pad(g, w) for g, w in zip(gloss, widths))
    return f'{prefix}{line1}\n{prefix}{line2}'


def unquote(translation):
    translation = translation.strip("'")
    translation = translation.replace("' / '", ' / ')
    translation = re.sub(r"(\s|\()'", r'\1', translation)
    translation = re.sub(r"'(\s|\))", r'\1', translation)
    translation = translation.replace("',", '; ')
    return translation  # noqa: RET504


def make_example(row):
    if row['Example:Material'] == '-':
        return None

    row_id = make_row_id(row)
    analysed = row['Example:Material'].replace(' \u0301', '\u0301')
    analysed = analysed.strip().split()
    gloss = row['Example:Glossing'].strip().split()
    translation = unquote(row['Example:Translation'])
    if len(analysed) != len(gloss):
        print('example {} ({}): ERR: misaligned gloss'.format(row_id, row['Language']))
        print(' ', row['Example:Material'])
        print(aligned_example(analysed, gloss, indent=2))
        print(f'  ‘{translation}’')
        print()

    source_comment = row.get('Example:Reference', '').strip()
    sources = [
        bibkey
        for bibkey in re.split(r'\s*;\s*', row.get('Example_Bibkeys', '').strip())
        if bibkey]

    return {
        'ID': row_id,
        'Language_ID': make_language_id(row),
        'Primary_Text': row['Example:Material'].strip(),
        'Analyzed_Word': row['Example:Material'].strip().split(),
        'Gloss': row['Example:Glossing'].strip().split(),
        'Translated_Text': translation,
        'Source': sources,
        'Source_comment': source_comment if not sources else '',
    }


def used_sources(bibliography, example_table):
    used_bibkeys = {
        src.split('[')[0] if '[' in src else src
        for example in example_table
        for src in example.get('Source', ())}
    entries = {
        bibkey: entry
        for bibkey, entry in bibliography.entries.items()
        if bibkey in used_bibkeys}
    return BibliographyData(entries=entries)


def make_forms(raw_data):
    forms = []
    for row in raw_data:
        row_id = make_row_id(row)
        language_id = make_language_id(row)
        forms.append({
            'ID': f'{row_id}-s',
            'Form': row['Source:Form'],
            'Language_ID': language_id,
            'Parameter_ID': slug(row['Source:Meaning_simplified'])})
        forms.append({
            'ID': f'{row_id}-t',
            'Form': row['Target:Form'],
            'Language_ID': language_id,
            'Parameter_ID': slug(row['Target:Meaning_simplified'])})
    return forms


def make_paths(raw_data):
    return [
        {
            'ID': (row_id := make_row_id(row)),
            'Source_Form_ID': f'{row_id}-s',
            'Target_Form_ID': f'{row_id}-t',
            'Subset': make_contrib_id(row),
            'Example_ID': row_id if row['Example:Material'] != '-' else '',
            'Comment': row.get('Comments'),
        }
        for row in raw_data]


def make_constructions(raw_data):
    return [
        {
            'ID': row_no,
            'Language_ID': make_language_id(row),
            'Name': 'Gram: {}'.format(row['Target:Meaning']),
            'Description': row['Target:Form'],
        }
        for row_no, row in enumerate(raw_data, 1)]


def normalise_cvalue(value):
    return value.lower()


def make_cvalues(raw_data, cparameters, ccodes):
    cvalues = []
    for row_no, row in enumerate(raw_data, 1):
        for col_name, parameter in cparameters.items():
            value = row.get(col_name)
            if not value:
                continue
            code = ccodes.get((parameter['ID'], normalise_cvalue(value)))
            cvalue = {
                'ID': '{}-{}'.format(row_no, parameter['ID']),
                'Construction_ID': row_no,
                'Parameter_ID': parameter['ID'],
                'Code_ID': code['ID'] if code else '',
                'Value': code['Name'] if code else value,
            }
            if parameter['ID'] == 'target-meaning-type':
                if (comment := row.get('Comments')):
                    cvalue['Comment'] = comment
            elif parameter['ID'] == 'source':
                cvalue['Comment'] = row['Source:Form']
                if row['Example:Material'] != '-':
                    cvalue['Example_IDs'] = [make_row_id(row)]
            cvalues.append(cvalue)
    return cvalues


def normalise_label_group(label_group):
    return label_group.lower()


def make_lvalues(raw_data, lparameters):
    label_groups = defaultdict(list)
    for row in raw_data:
        language_id = make_language_id(row)
        label_group = normalise_label_group(row['Target:Label_Group'])
        form = {
            'form': row['Target:Form'],
            'meaning': row['Target:Meaning'],
        }

        if label_group in lparameters:
            label_groups[language_id, label_group].append(form)
        else:
            print(
                f'{language_id}: target form ‘{form}’:',
                f'unknown label group {label_group}')
    return [
        {
            'Language_ID': language_id,
            'Parameter_ID': (param_id := lparameters[label_group]['ID']),
            'ID': f'{language_id}-{param_id}',
            'Value': ' / '.join(form['meaning'] for form in forms),
            'Comment': ' / '.join(form['form'] for form in forms),
            'Description': row['Target:Meaning'],
        }
        for (language_id, label_group), forms in label_groups.items()]


def define_wordlist_schema(cldf):
    cldf.add_component('LanguageTable', 'Family')
    cldf.add_component('ContributionTable')
    cldf.add_component(
        'ExampleTable',
        'http://cldf.clld.org/v1.0/terms.rdf#source',
        'Source_comment')
    cldf.add_columns('FormTable', 'Type')
    cldf.add_table(
        'paths.csv',
        'http://cldf.clld.org/v1.0/terms.rdf#id',
        'http://cldf.clld.org/v1.0/terms.rdf#sourceFormReference',
        'http://cldf.clld.org/v1.0/terms.rdf#targetFormReference',
        'http://cldf.clld.org/v1.0/terms.rdf#comment',
        {"name": "Subset",
         "datatype": "string",
         "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#contributionReference"},
        'http://cldf.clld.org/v1.0/terms.rdf#exampleReference')


def define_crossgram_schema(cldf):
    cldf.add_component('LanguageTable', 'Family')
    cldf.add_component(
        'ExampleTable',
        'http://cldf.clld.org/v1.0/terms.rdf#source',
        'Source_comment')
    cldf.add_table(
        'constructions.csv',
        'http://cldf.clld.org/v1.0/terms.rdf#id',
        'http://cldf.clld.org/v1.0/terms.rdf#languageReference',
        'http://cldf.clld.org/v1.0/terms.rdf#name',
        'http://cldf.clld.org/v1.0/terms.rdf#description')
    cldf.add_table(
        'cvalues.csv',
        'http://cldf.clld.org/v1.0/terms.rdf#id',
        {'name': 'Construction_ID',
         'datatype': {'base': 'string', 'format': '[a-zA-Z0-9_\\-]+'},
         'required': True},
        'http://cldf.clld.org/v1.0/terms.rdf#parameterReference',
        'http://cldf.clld.org/v1.0/terms.rdf#codeReference',
        'http://cldf.clld.org/v1.0/terms.rdf#value',
        'http://cldf.clld.org/v1.0/terms.rdf#source',
        'http://cldf.clld.org/v1.0/terms.rdf#comment',
        {'name': 'Example_IDs',
         'datatype': {'base': 'string', 'format': '[a-zA-Z0-9_\\-]+'},
         'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#exampleReference',
         'separator': ';'})

    cldf.add_foreign_key(
        'cvalues.csv', 'Construction_ID', 'constructions.csv', 'ID')


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "magram"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return {
            None: CLDFSpec(
                dir=self.cldf_dir,
                module='Wordlist',
                data_fnames={'ParameterTable': 'concepts.csv'}),
            'crossgram': CLDFSpec(
                dir=self.cldf_dir,
                module='StructureDataset',
                metadata_fname='CrossGram-metadata.json',
                data_fnames={
                    'ParameterTable': 'crossgram-parameters.csv',
                    'CodeTable': 'crossgram-codes.csv'}),
        }

    def cmd_readme(self, _args):
        header_letters = 'abcdefghijklmnopqrstuvwxyz0123456789-_'

        def _toc_entry(header):
            if header.startswith('### '):
                header_text = header.lstrip('# ')
                header_id = ''.join(
                    c
                    for c in header_text.lower().replace(' ', '-')
                    if c in header_letters)
                return f'  - [{header_text}](#{header_id})'
            elif header.startswith('## '):
                header_text = header.lstrip('# ')
                header_id = ''.join(
                    c
                    for c in header_text.lower().replace(' ', '-')
                    if c in header_letters)
                return f'- [{header_text}](#{header_id})'
            else:
                raise AssertionError('UNREACHABLE')

        intro_text = self.raw_dir.read('intro-template.md')
        prefix = [
            'MAGRAM, the MAinz GRAMmaticalization data base',
            '==============================================',
            '',
        ]
        prefix.extend(
            _toc_entry(line)
            for line in intro_text.splitlines()
            if line.startswith(('## ', '### ')))
        prefix.append('- [CLDF Datasets](#cldf-datasets)')
        prefix.append('')
        intro_template = Template(intro_text)
        return intro_template.substitute(
            prefix='\n'.join(prefix),
            workflowdiagram='![Workflow Diagram](workflow.png)')

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        # read data

        raw_data = parse_raw_data(
            self.raw_dir.read_csv('MAGRAM_database.csv', dicts=True))
        raw_data.sort(key=lambda row: make_language_id(row))
        cparameters = {
            row['Original_Column_Name']: row
            for row in self.etc_dir.read_csv('cparameters.csv', dicts=True)}
        lparameters = {
            row['Original_Name']: row
            for row in self.etc_dir.read_csv('lparameters.csv', dicts=True)}
        ccodes = parse_ccodes(
            self.etc_dir.read_csv('ccodes.csv', dicts=True))

        bibfile = self.raw_dir / 'MAGRAM_database_example_reference_bibliography.bib'
        bibliography = parse_file(bibfile)

        languoids = get_languoids(args.glottolog.api, raw_data)

        # make cldf data

        # shared tables
        languages = make_languages(raw_data, languoids)
        example_table = [
            example
            for row in raw_data
            if (example := make_example(row))]
        bibliography = used_sources(bibliography, example_table)

        # wordlist tables
        contributions = make_contributions(raw_data)
        concepts = make_concepts(raw_data)
        form_table = make_forms(raw_data)
        path_table = make_paths(raw_data)

        # crossgram tables
        constructions = make_constructions(raw_data)
        cvalues = make_cvalues(raw_data, cparameters, ccodes)
        lvalues = make_lvalues(raw_data, lparameters)

        # write cldf data

        intro_template = Template(self.raw_dir.read('intro-template.md'))
        intro_text = intro_template.substitute(
            prefix='',
            workflowdiagram=ASCII_DIAGRAM)
        with open(self.raw_dir / 'intro.md', 'w', encoding='utf-8') as f:
            print(intro_text, end='', file=f)

        with self.cldf_writer(args) as writer:
            define_wordlist_schema(writer.cldf)
            writer.objects['LanguageTable'] = languages.values()
            writer.objects['ExampleTable'] = example_table
            writer.objects['ParameterTable'] = concepts.values()
            writer.objects['ContributionTable'] = contributions.values()
            writer.objects['FormTable'] = form_table
            writer.objects['paths.csv'] = path_table
            writer.cldf.add_sources(bibliography)

        with self.cldf_writer(args, cldf_spec='crossgram', clean=False) as writer:
            define_crossgram_schema(writer.cldf)
            # LanguageTable and ExampleTable are being reused from the wordlist
            writer.objects['constructions.csv'] = constructions
            writer.objects['ParameterTable'] = list(chain(
                lparameters.values(),
                cparameters.values()))
            writer.objects['CodeTable'] = ccodes.values()
            writer.objects['cvalues.csv'] = cvalues
            writer.objects['ValueTable'] = lvalues
            writer.cldf.add_sources(bibliography)
