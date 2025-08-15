import click
from app import create_app, db
from app.models import User

@click.group()
def cli():
    pass

@cli.command("create-initial-user")
@click.option("--email", required=True)
@click.option("--name", required=True)
@click.option("--role", required=True, type=click.Choice(["ADMIN","COMPRADOR","REQUISITANTE","FORNECEDOR"], case_sensitive=False))
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_initial_user(email, name, role, password):
    app = create_app()
    with app.app_context():
        if User.query.filter_by(email=email.lower()).first():
            click.echo("User already exists")
            return
        u = User(email=email.lower(), name=name, role=role.upper(), active=True)
        u.set_password(password)
        db.session.add(u); db.session.commit()
        click.echo(f"Created {role} {email}")

if __name__ == "__main__":
    cli()
