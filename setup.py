from setuptools import setup


setup(
    name='cldfbench_magram',
    py_modules=['cldfbench_magram'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'magram=cldfbench_magram:Dataset',
        ]
    },
    install_requires=[
        'cldfbench[glottolog]',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
