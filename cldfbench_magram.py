import pathlib

from clldutils.misc import slug
from cldfbench import Dataset as BaseDataset, CLDFSpec

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


def make_languages(raw_data):
    languages = {}
    for row in raw_data:
        if (language_id := make_language_id(row)) not in languages:
            languages[language_id] = {
                'ID': language_id,
                'Name': row['Language'],
                'Glottocode': row['Glottocode'],
            }
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


def make_example(row):
    row_id = make_row_id(row)
    analysed = row['Example:Material'].replace(' \u0301', '\u0301')
    analysed = analysed.strip().split()
    gloss = row['Example:Glossing'].strip().split()
    if len(analysed) != len(gloss):
        print('{} - {}'.format(row_id, row['Example:Material']))
        print('\t'.join(analysed))
        print('\t'.join(gloss))
        print()
    return {
        'ID': row_id,
        'Language_ID': make_language_id(row),
        'Primary_Text': row['Example:Material'].strip(),
        'Analyzed_Word': row['Example:Material'].strip().split(),
        'Gloss': row['Example:Glossing'].strip().split(),
        'Translated_Text': row['Example:Translation'],
        # FIXME: 'Example:Reference'
    }


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
            'Example_ID': row_id,
        }
        for row in raw_data]


def make_constructions(raw_data):
    return [
        {
            'ID': row_no,
            'Language_ID': make_language_id(row),
            'Name': 'Gram: {}'.format(row['Target:Form']),
            'Description': row['Target:Meaning'],
        }
        for row_no, row in enumerate(raw_data, 1)]


def make_cvalues(raw_data, cparameters, ccodes):
    cvalues = []
    for row_no, row in enumerate(raw_data, 1):
        for col_name, parameter in cparameters.items():
            value = row[col_name]
            if not value:
                continue
            code = ccodes.get((parameter['ID'], value))
            cvalue = {
                'ID': '{}-{}'.format(row_no, parameter['ID']),
                'Construction_ID': row_no,
                'Parameter_ID': parameter['ID'],
                'Code_ID': code['ID'] if code else '',
                'Value': code['Name'] if code else value,
            }
            if parameter['ID'] == 'source-form':
                cvalue['Comment'] = row['Source:Meaning']
                cvalue['Example_IDs'] = [make_row_id(row)]
            cvalues.append(cvalue)
    return cvalues


def define_wordlist_schema(cldf):
    cldf.add_component('LanguageTable')
    cldf.add_component('ContributionTable')
    cldf.add_component('ExampleTable')
    cldf.add_columns('FormTable', 'Type')
    cldf.add_table(
        'paths.csv',
        'http://cldf.clld.org/v1.0/terms.rdf#id',
        'http://cldf.clld.org/v1.0/terms.rdf#sourceFormReference',
        'http://cldf.clld.org/v1.0/terms.rdf#targetFormReference',
        {"name": "Subset",
         "datatype": "string",
         "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#contributionReference"},
        'http://cldf.clld.org/v1.0/terms.rdf#exampleReference')


def define_crossgram_schema(cldf):
    cldf.add_component('LanguageTable')
    cldf.add_component('ExampleTable')
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
        {'name': 'Example_IDs',
         'datatype': {'base': 'string', 'format': '[a-zA-Z0-9_\\-]+'},
         'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#exampleReference',
         'separator': ';'},
        'http://cldf.clld.org/v1.0/terms.rdf#source',
        'http://cldf.clld.org/v1.0/terms.rdf#value')

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
        ccodes = parse_ccodes(
            self.etc_dir.read_csv('ccodes.csv', dicts=True))

        # make cldf data

        # shared tables
        languages = make_languages(raw_data)
        example_table = list(map(make_example, raw_data))

        # wordlist tables
        contributions = make_contributions(raw_data)
        concepts = make_concepts(raw_data)
        form_table = make_forms(raw_data)
        path_table = make_paths(raw_data)

        # crossgram tables
        constructions = make_constructions(raw_data)
        cvalues = make_cvalues(raw_data, cparameters, ccodes)

        # write cldf data

        with self.cldf_writer(args) as writer:
            define_wordlist_schema(writer.cldf)
            writer.objects['LanguageTable'] = languages.values()
            writer.objects['ExampleTable'] = example_table
            writer.objects['ParameterTable'] = concepts.values()
            writer.objects['ContributionTable'] = contributions.values()
            writer.objects['FormTable'] = form_table
            writer.objects['paths.csv'] = path_table

        with self.cldf_writer(args, cldf_spec='crossgram', clean=False) as writer:
            define_crossgram_schema(writer.cldf)
            # LanguageTable and ExampleTable are being reused from the wordlist
            writer.objects['constructions.csv'] = constructions
            writer.objects['ParameterTable'] = cparameters.values()
            writer.objects['CodeTable'] = ccodes.values()
            writer.objects['cvalues.csv'] = cvalues
            writer.objects['ValueTable'] = []
