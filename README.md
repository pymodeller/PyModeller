# PyModeller

<p align="center">

![Python](https://img.shields.io/badge/Python-3.13%2B-3775A8?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-0.5+-00A1E0?logo=uv&logoColor=white)
[![License](https://img.shields.io/github/license/pymodeller/pymodeller?color=green)](LICENSE)

[![Tests](https://img.shields.io/github/actions/workflow/status/pymodeller/pymodeller/tests.yml?label=Tests&logo=github)](https://github.com/pymodeller/pymodeller/actions)
[![CI](https://img.shields.io/github/actions/workflow/status/pymodeller/pymodeller/ci.yml?label=CI&logo=github)](https://github.com/pymodeller/pymodeller/actions)
[![Coverage](https://img.shields.io/codecov/c/github/pymodeller/pymodeller?logo=codecov&logoColor=white)](https://app.codecov.io/gh/pymodeller/pymodeller)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

</p>



Pymodeller is a powerful CLI tool designed to bridge the gap between configuration specifications and Python code. By using a single YAML source of truth, you can automate the generation of Pydantic models, Peewee ORM classes, and manage environment variables with ease.

## Features

 * Code Generation: Automatically generate typed Pydantic models or Peewee schemas.
 * Environment Management: Create .env.example templates directly from your spec.
 * Validation: Ensure your local .env files stay in sync with your definitions.
 * Drift Detection: Identify discrepancies between your YAML specification and your generated Python code.

 ---

## Installation

 Install pymodeller via pip:

 '''bash  
 pip install pymodeller
'''

 ---

## Usage

 The CLI provides four main commands to manage your development workflow:

### 1. Code Generation
 Generate typed Pydantic models or Peewee code for your project.
 bash  pymodeller codegen --input schema.yaml --output models.py

### 2. Example Environment Generation
 Generate a template .env.example file based on your YAML specification to help collaborators set up their environment.
 bash  pymodeller example --input schema.yaml

### 3. Environment Check
 Validate your current .env file against the YAML specification to ensure all required variables are present and correctly formatted.
 bash  pymodeller check --env .env --spec schema.yaml

### 4. Drift Detection
 Check for "drift" between your YAML specification and the code already generated. This ensures that your Python models haven't fallen out of date.
 bash  pymodeller drift --input schema.yaml --code models.py

 ---

## CLI Command Reference

<p align="center">
  <img src="docs/assets/cli.png" alt="pymodeller cli">
</p>
 ---

## Example YAML Specification

 Your py_modeller.yaml should define the structure of your models. See file: py_modeller.yaml


 ---

## Contributing

 Contributions are welcome! Please feel free to submit a Pull Request or open an issue if you find a bug or have a feature request.

## License

 This project is licensed under the MIT License.
