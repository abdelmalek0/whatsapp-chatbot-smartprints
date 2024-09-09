import yaml
import os

def load_template(template_name):
    template_path = os.path.join('templates', f'{template_name}.yaml')
    with open(template_path, 'r') as file:
        return yaml.safe_load(file)['prompt']