import pathlib
import itertools

from clldutils.misc import slug
from cldfbench import Dataset as BaseDataset, CLDFSpec


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "magram"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(dir=self.cldf_dir, module='Wordlist')

    def cmd_download(self, args):
        pass

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ContributionTable')
        args.writer.cldf.add_component('ParameterTable')
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
        concepts, contribs = set(), set()

        for lid, rows in itertools.groupby(
            sorted(
                self.raw_dir.read_csv('MAGRAM_database.csv', dicts=True),
                key=lambda r: slug(r['Language'])),
            lambda r: slug(r['Language']),
        ):
            """
            1 Code, 
            2 Subset, 
            3 Data_Source, 
            4 Author(s), 
            5 Macro-Area_Dryer, 
            6 Macro-Area_Hammarström_Donohue, 
            7 Family, 
            8 Glottocode, 
            9 ISO 639-3, 
            10 Genus, 
            11 Language, 
            12 level_of_reconstruction_if_applicable, 
            13 Source:Form, 
            14 Source:Meaning, 
            15 Source:Meaning_simplified, 
            16 Source:Label_Group, 
            17 Target:Form, 
            18 Target:Meaning, 
            19 Target:Meaning_simplified, 
            20 Target:Label_Group, 
            Example:Material, 
            Example:Glossing, 
            Example:Translation, 
            Example:Reference, 
            Comments, 
            value:semantic_integrity, 
            value:phonetic_reduction, 
            value:paradigmaticity, 
            value:bondedness, 
            value:paradigmatic_variability, 
            value:syntagmatic_variability, 
            value:decategorization, 
            value:allomorphy, 
            change:semantic_integrity, 
            change:phonetic_reduction, 
            change:paradigmaticity, 
            change:bondedness, 
            change:paradigmatic_variability, 
            change:syntagmatic_variability, 
            change:decategorization, 
            change:allomorphy
            """
            rows = list(rows)
            row = rows[0]
            args.writer.objects['LanguageTable'].append(
                dict(ID=lid, Name=row['Language'], Glottocode=row['Glottocode']))
            for row in rows:
                rid = '{}-{}-{}-{}'.format(row['Code'], slug(row['Source:Form']), slug(row['Target:Form']), slug(row['Target:Meaning_simplified']))
                for m in ['Target:Meaning_simplified', 'Source:Meaning_simplified']:
                    if slug(row[m]) not in concepts:
                        concepts.add(slug(row[m]))
                        args.writer.objects['ParameterTable'].append(
                            dict(ID=slug(row[m]), Name=row[m]))
                if row['Subset'] not in contribs:
                    contribs.add(row['Subset'])
                    args.writer.objects['ContributionTable'].append(dict(ID=slug(row['Subset']), Name=row['Subset']))
                args.writer.objects['FormTable'].extend([
                    dict(ID='{}-s'.format(rid), Form=row['Source:Form'], Language_ID=lid, Parameter_ID=slug(row['Source:Meaning_simplified'])),
                    dict(ID='{}-t'.format(rid), Form=row['Target:Form'], Language_ID=lid, Parameter_ID=slug(row['Target:Meaning_simplified'])),
                ])
                a = row['Example:Material'].replace(' \u0301', '\u0301').strip().split()
                g = row['Example:Glossing'].strip().split()
                if len(a) != len(g):
                    print('{} - {}'.format(rid, row['Example:Material']))
                    print('\t'.join(a))
                    print('\t'.join(g))
                    print('')
                args.writer.objects['ExampleTable'].append(dict(
                    ID=rid,
                    Language_ID=lid,
                    Primary_Text=row['Example:Material'].strip(),
                    Analyzed_Word=row['Example:Material'].strip().split(),
                    Gloss=row['Example:Glossing'].strip().split(),
                    Translated_Text=row['Example:Translation'],
                    # FIXME: Example:Reference
                ))
                args.writer.objects['paths.csv'].append(dict(
                    ID=rid,
                    Source_Form_ID='{}-s'.format(rid),
                    Target_Form_ID='{}-t'.format(rid),
                    Subset=slug(row['Subset']),
                    Example_ID=rid,
                ))
