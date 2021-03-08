import click
from .main import main
import requests
from scaleout.auth import login, get_stackn_config, get_remote_config, get_token
from .helpers import create_table, search_for_model, new_id, Determinant
import os
import random
import string
import json
import uuid
import subprocess


# @click.option('--daemon',
#               is_flag=True,
#               help=(
#                       "Specify to run in daemon mode."
#               )
#               )

@main.command('setup')
@click.option('--secure/--insecure', default=True)
@click.pass_context
def setup_cmd(ctx, secure):
    login(secure=secure)

@main.command('login')
@click.option('--secure/--insecure', default=True)
@click.pass_context
def login_cmd(ctx, secure):
    stackn_config, load_status = get_stackn_config(secure=secure)
    if not load_status:
        print('Failed to load STACKn config.')
        return

    remote_config, load_status = get_remote_config()
    if remote_config:
        login(deployment=stackn_config['active'],
              keycloak_host=remote_config['keycloak_url'],
              studio_host=remote_config['studio_url'])

@main.command('status')
@click.pass_context
def status_cmd(ctx):
    stackn_config, load_status = get_stackn_config()
    if not load_status:
        print('Failed to load STACKn config.')
    else:
        print('Context: '+stackn_config['active'])
        if 'active_project' in stackn_config:
            print('Project: '+stackn_config['active_project'])
        else:
            print('No active project; create a new project or set an existing project.')

@main.command('predict')
@click.option('-m', '--model', required=True)
@click.option('-v', '--version')
@click.option('-i', '--inp', required=True)
@click.pass_context
def predict_cmd(ctx, model, version, inp):
    client = ctx.obj['CLIENT']
    client.predict(model, inp, version)
    # token, config = get_token()
    # res = requests.post(url,
    #                     headers={"Authorization": "Token "+token},
    #                     json = inp)

@main.command('train')
@click.option('--log-off', flag_value='log-off', default=False)
@click.option('-m', '--model', prompt=True, cls=Determinant, determinant='log_off')
@click.option('-i', '--run-id', required=False, default=str(uuid.uuid1().hex))
@click.option('-f', '--training-file', required=False, default="src/models/train.py")
#@click.option('-c', '--code-version', prompt=True, cls=Determinant, determinant='log_off')
@click.option('-v', '--model-version', default='latest')
@click.pass_context
def train_cmd(ctx, log_off, model, run_id, training_file, model_version=[]):
    """ Train a model and log metadata """
    
    if os.path.isfile('src/models/tracking/metadata/{}.pkl'.format(run_id)): 
        run_id = new_id(run_id)
    print("Preparing to start training session with '{}' as unique ID.".format(run_id))
    if os.path.isfile(training_file):
        if log_off:
            subprocess.run(['python', training_file, run_id])
        else:
            model_exists = search_for_model(ctx, "models", model) 
            if model_exists:
                client = ctx.obj['CLIENT']
                client.train(model, model_version, run_id, training_file)
            else: 
                print("The model '{}' does not exist in the active project and cannot be trained.".format(model))
    else:
        current_dir = os.getcwd()
        print("Could not start a training session. Check that you have initialized a model "\
            + "in '{}' and that the file '{}' exists.".format(current_dir, training_file))


@main.command('dvc')
@click.pass_context
def dvc_cmd(ctx):
    stackn_config, load_status = get_stackn_config()
    if not load_status:
        print('Failed to load STACKn config.')
    else:
        if 'active_project' in stackn_config:
            client = ctx.obj['CLIENT']
            if not os.path.isdir('.dvc'):
                print("Checking for local DVC installation:")
                version_control = subprocess.run(["dvc", "version"], stdout=subprocess.PIPE, text=True)
                if version_control.returncode == 0:
                    print("\n{}".format(version_control.stdout))
                    client.dvc_init("install")
                else:
                    print("DVC is not installed on your local system. Please install DVC before initializing a dvc setup with 'stackn dvc'")
            else:
                print('DVC config already exists in current directory.')
        else:
            print("No active project in STACKn config; set an existing project as active using 'stackn set project -p <name of project>'")
        
@main.command('run')
@click.option('--log-off', flag_value='log-off', default=False)
@click.option('-m', '--model', prompt=True, cls=Determinant, determinant='log_off')
@click.option('-i', '--run-id', required=False, default=str(uuid.uuid1().hex))
@click.option('-f', '--config-file', required=False, default="pipeline.json")
@click.option('-v', '--model-version', default='latest')
@click.pass_context
def run_cmd(ctx, log_off, model, run_id, config_file, model_version=[]):
    """ Conduct experiment as specified in pipeline.json """

    try:
        with open(config_file) as f:
            data = json.load(f)
        if log_off:
            import subprocess
            if data["requirements"]:
                print("Installing requirements")
                subprocess.run(['pip', 'install', '-r', 'requirements.txt'])
            for file_name, exp_file in data["pipeline"].items():
                try:
                    print("Running file '{}'".format(file_name))
                    subprocess.run(['python', exp_file])
                except Exception as e:
                    print("Experiment failed.")
                    print("Reason: {}".format(e))
        else:
            model_exists = search_for_model(ctx, "models", model)
            if model_exists:
                client = ctx.obj['CLIENT']
                client.run(model, model_version, run_id, data)
            else: 
                print("The model '{}' does not exist in the active project.".format(model)) 
    except Exception as e:
        print("Could not start experiment.")
        print("Reason: {}".format(e))
