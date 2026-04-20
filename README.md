# PyModeller

<p align="center">

![Python](https://img.shields.io/badge/Python-3.13%2B-3775A8?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-0.5+-00A1E0?logo=uv&logoColor=white)
[![License](https://img.shields.io/github/license/pymodeller/PyModeller?color=green)](LICENSE)

[![Tests](https://img.shields.io/github/actions/workflow/status/pymodeller/PyModeller/tests.yaml?label=Tests&logo=github)](https://github.com/pymodeller/pymodeller/actions)
[![CI](https://img.shields.io/github/actions/workflow/status/pymodeller/PyModeller/ci.yml?label=CI&logo=github)](https://github.com/pymodeller/pymodeller/actions)
[![Coverage](https://img.shields.io/codecov/c/github/pymodeller/PyModeller?logo=codecov&logoColor=white)](https://app.codecov.io/gh/pymodeller/pymodeller)
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

```bash
 uv add pymodeller
```

 ---

## Usage

 The CLI provides four main commands to manage your development workflow:

### 1. Code Generation
 Generate typed Pydantic models or Peewee code for your project.
```bash  
pymodeller codegen --input schema.yaml --output models.py
```

### 2. Example Environment Generation
 Generate a template .env.example file based on your YAML specification to help collaborators set up their environment.
```bash  
pymodeller example --input schema.yaml
```

### 3. Environment Check
 Validate your current .env file against the YAML specification to ensure all required variables are present and correctly formatted.
```bash  
pymodeller check --env .env --spec schema.yaml
```

### 4. Drift Detection
 Check for "drift" between your YAML specification and the code already generated. This ensures that your Python models haven't fallen out of date.
```bash  
pymodeller drift --input schema.yaml --code models.py
```

 ---

## CLI Command Reference

<p align="center">
  <img src="assets/cli.png" alt="pymodeller cli">
</p>
 ---

## Data Loading & Specification

The project uses a structured YAML-to-Object mapping to manage environment variables and database schemas.
The py_modeller.yaml acts as the Single Source of Truth, which is parsed into an EnvSpec instance.


## 1. YAML Configuration Example

The py_modeller.yaml file defines the structure of your environment and database models. Below is an example of how to configure sections, variables, and nested models:

```yaml 
# Global configuration for output paths 
config: 
  - name: PYDANTIC_OUT   # master config_models
    value: src/models/config_models.py 
  - name: PEEWEE_OUT    # master config peewee
    value: src/models/db_models.py 
  - name: PYDANTIC_FOLDER  # pydantic: output pydantic models folder
    value: src/paper_hough/models
  - name: PEEWEE_FOLDER  # peewee: output orm folder
    value: src/paper_hough/models/db  
  
sections: 
  # 1. Settings Section: Used for application-wide flags 
  - name: General 
    description: Top-level application flags 
    type: settings 
    variables: 
      - name: LOCAL_DEV 
        description: Enable local development mode 
        type: bool 
        default: "true" 
      - name: API_KEY 
        description: Secure token for external services 
        type: secret  # Automatically handled as str + secret: true 
        required: true 
 
  # 2. Model Section: Defines data structures and types 
  - name: Algorithm 
    description: Configuration for processing logic 
    type: model 
    env_prefix: HOUGH 
    variables: 
      - name: THRESHOLD 
        type: int 
        default: "100" 
      - name: MATRIX_DATA 
        description: Raw matrix input 
        type: pnd.NpNDArrayUint8 # Specialized numpy-pydantic type 
        required: true 
 
  # 3. Database Integration: Mapping fields to DB specs 
  - name: UserProfile
    description: Database schema for users 
    type: model 
    database: 
      table_name: users 
      primary_key: ["id"] 
    variables: 
      - name: USERNAME 
        type: str 
        db_spec: 
          max_length: 50 
          unique: true 
          allow_null: false 
 
  # 4. Nested Models & Lists 
  - name: ProcessingQueue 
    type: settings 
    variables: 
      - name: ITEMS 
        description: List of algorithm configurations 
        from_model: Algorithm # Reference to another section 
        type: list 
        required: true 
```

### Key Mapping Features:
* Type Normalization: Keywords like integer, bool, or path are automatically mapped to Python types.
* Secret Sugar: Setting type: secret is a shortcut that sets the type to str and enables the secret flag for masking.
* Automatic Aliasing: A variable named SERVER_HOST in YAML will be accessible as serverHost in Python via camelCase conversion.
* Model Reusability: Use from_model to create complex, nested structures from existing sections.

### 2. Object Hierarchy
* EnvSpec: The root object containing all configuration sections.
* EnvSection: Groups variables logically (e.g., General, Algorithm).
    * Supports env_prefix to namespace variables in the shell.
    * Can optionally hold a DBSpec for table-level database metadata.
* EnvVarSpec: Defines individual settings.
    * Automatic Aliasing: Converts SNAKE_CASE names to camelCase attributes automatically during __post_init__.
    * Secret Handling: If type: secret is used in YAML, it is normalized to str but flagged as hidden for logs/documentation.
* DBField: Detailed field-level constraints for Peewee ORM integration (lengths, nullability, foreign keys, etc.).

### 3. Validation
The loading process includes a mandatory validate_no_duplicates() call which ensures:
1. No two environment variables share the same env_name.
2. No two Python attributes (aliases) collide within the same section.


## Example YAML Specification

 Your py_modeller.yaml should define the structure of your models. See file: py_modeller.yaml


 ---

## Contributing

 Contributions are welcome! Please feel free to submit a Pull Request or open an issue if you find a bug or have a feature request.

## License

 This project is licensed under the MIT License.
