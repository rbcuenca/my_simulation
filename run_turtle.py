#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import subprocess
import os
from ament_index_python.packages import get_package_share_directory
import random

# Defina as coordenadas da caixa
x = random.uniform(-3, 3)
y = -2
z = 0.25

launch_file_dir = os.path.join(get_package_share_directory('my_gazebo'), 'launch')
pkg_gazebo_ros = get_package_share_directory('gazebo_ros')

world = os.path.join(
        get_package_share_directory('my_gazebo'),
        'worlds',
        'run_turtle_run.world'
    )

# Crie o arquivo .world dinamicamente
root = ET.Element("world", name="meu_mundo")

tree = ET.parse(world)
root = tree.getroot()

for model in root.findall('.//model'):
    if model.get('name') == 'caixa_lateral_esquerda':
        pose = model.find('pose')
        pose.set('frame', '')
        pose.text = f"{x} {y} {z} 0 0 0"  
tree.write(world)

try:
    command = f"cb"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    command = f"ros2 launch my_gazebo run_turtle.launch.py"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Erro ao executar o comando: {result.stderr}")
    else:
        print("Comando executado com sucesso.")
except KeyboardInterrupt:
    print("Ctrl+C pressionado. Fehcando o Gazebo!")
    os.system ("pkill -9 ros2")