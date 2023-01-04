# Nice Run!

Nice Run! is a simple web app to create screenshot of running activities that can be shared on social media.

It's a work in progress, but it's close to being _usable_ by others.

## Example

![](https://media.brntn.me/postie/6775f5ae.png)

(overall look and feel evolving...)

## Usage

### Running the initial migrations

```bash
pipenv run python manage.py migrate
```

### Running the development server

```bash
pipenv run python manage.py runserver
```

### Running the tests

```bash
pipenv run python manage.py test
```

### Deploying to a VPS

Notes:

- Ansible must be installed on your local machine
- Target should be running Debian 11

```bash
pipenv run python manage.py up nice-run.com --email=<your-email>
```

---

Generated with [sesh/djbs](https://github.com/sesh/djbs).
