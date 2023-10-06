import pathlib

from clldutils.misc import slug
from cldfbench import Dataset as BaseDataset, CLDFSpec


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


def make_example(row):
    row_id = make_row_id(row)
    analysed = row['Example:Material'].replace(' \u0301', '\u0301')
    analysed = analysed.strip().split()
    gloss = row['Example:Glossing'].strip().split()
    if len(analysed) != len(gloss):
        print('{} - {}'.format(row_id, row['Example:Material']))
        print('\t'.join(analysed))
        print('\t'.join(gloss))
        print('')
    return {
        'ID': row_id,
        'Language_ID': make_language_id(row),
        'Primary_Text': row['Example:Material'].strip(),
        'Analyzed_Word': row['Example:Material'].strip().split(),
        'Gloss': row['Example:Glossing'].strip().split(),
        'Translated_Text': row['Example:Translation'],
        # FIXME: 'Example:Reference'
    }


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "magram"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(dir=self.cldf_dir, module='Wordlist')

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        raw_data = self.raw_dir.read_csv('MAGRAM_database.csv', dicts=True)
        raw_data.sort(key=lambda row: make_language_id(row))

        language_table = {}
        for row in raw_data:
            if (language_id := make_language_id(row)) not in language_table:
                language_table[language_id] = {
                    'ID': language_id,
                    'Name': row['Language'],
                    'Glottocode': row['Glottocode'],
                }

        contribution_table = {}
        for row in raw_data:
            if (contrib_id := make_contrib_id(row)) not in contribution_table:
                contribution_table[contrib_id] = {
                    'ID': contrib_id,
                    'Name': row['Subset'],
                }

        concept_table = {}
        for row in raw_data:
            target_id = slug(row['Target:Meaning_simplified'])
            if target_id not in concept_table:
                concept_table[target_id] = {
                    'ID': target_id,
                    'Name': row['Target:Meaning_simplified'],
                }
            source_id = slug(row['Source:Meaning_simplified'])
            if source_id not in concept_table:
                concept_table[source_id] = {
                    'ID': source_id,
                    'Name': row['Source:Meaning_simplified'],
                }

        example_table = list(map(make_example, raw_data))

        form_table = []
        for row in raw_data:
            row_id = make_row_id(row)
            language_id = make_language_id(row)
            form_table.append({
                'ID': '{}-s'.format(row_id),
                'Form': row['Source:Form'],
                'Language_ID': language_id,
                'Parameter_ID': slug(row['Source:Meaning_simplified'])})
            form_table.append({
                'ID': '{}-t'.format(row_id),
                'Form': row['Target:Form'],
                'Language_ID': language_id,
                'Parameter_ID': slug(row['Target:Meaning_simplified'])})

        path_table = [
            {
                'ID': (row_id := make_row_id(row)),
                'Source_Form_ID': '{}-s'.format(row_id),
                'Target_Form_ID': '{}-t'.format(row_id),
                'Subset': make_contrib_id(row),
                'Example_ID': row_id,
            }
            for row in raw_data]

        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ParameterTable')
        args.writer.cldf.add_component('ContributionTable')
        args.writer.cldf.add_component('ExampleTable')
        args.writer.cldf.add_columns('FormTable', 'Type')
        args.writer.cldf.add_table(
            'paths.csv',
            {
                "name": "ID",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id",
            },
            {
                "name": "Source_Form_ID",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#sourceFormReference",
            },
            {
                "name": "Target_Form_ID",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#targetFormReference",
            },
            {
                "name": "Subset",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#contributionReference",
            },
            {
                "name": "Example_ID",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#exampleReference",
            },
        )

        args.writer.objects['LanguageTable'] = language_table.values()
        args.writer.objects['ParameterTable'] = concept_table.values()
        args.writer.objects['ContributionTable'] = contribution_table.values()
        args.writer.objects['ExampleTable'] = example_table
        args.writer.objects['FormTable'] = form_table
        args.writer.objects['paths.csv'] = path_table
