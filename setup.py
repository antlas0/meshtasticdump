from setuptools import setup, find_packages


def parse_requirements(filename):
    with open(filename, 'r') as file:
        lines = file.read().splitlines()
        requirements = [
            line for line in lines if line and not line.startswith('#')
            ]
    return requirements


requirements = parse_requirements('requirements.txt')


setup(
    name="meshtasticdump",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
    author="antlas0",
)