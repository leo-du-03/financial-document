# Financial Document Question Answering System

Welcome!

<hr>

## 💼 Background 

Here, we're creating a system that enables users to ask questions in natural language and receive answers based on relevant financial documents!

<hr>

## 🧰 Setup

To install and setup the project:

1. Clone the repository to your computer
2. Set up a Python environment and install packages
   ```
   pip install -r requirements.txt
   ```
3. Add a `secrets.toml` file under the .streamlit directory following the example of `secrets.toml.example`
4. Add a file called `.env` to the root directory, with the phrase `DATABASE_URL={URL TO YOUR DATABASE HERE}` to store logs.
5. Run the following command to initialize the Prisma database:
   `prisma db push`
6. Install wkhtmltopdf here: https://wkhtmltopdf.org/
      - add it to the path if you're on windows
7. Run the streamlit file
   ```
   streamlit run app.py
   ```

<hr>

## Unit Testing

To conduct unit testing, we're relying on Python's own `unittest` package.

To execute tests:
```
python tests/test.py
```

<hr>

## Linting

Automated linting will occur when a pull request is made.
We are using the `ruff` linter.

To download ruff with pip:
```
pip install ruff
```

To run ruff:
```
ruff check
```

Please run ruff before you make a pull request!
