import numpy as np
import rclpy
from rclpy.node import Node
from robcomp_interfaces.msg import Conversation
import random

"""
ros2 topic pub /handler robcomp_interfaces/msg/Conversation "{history: [], message: 'Robo: Bifurcação: 100'}"
"""

class HandlerNode(Node):

    def __init__(self):
        super().__init__('handler_node_24b_af')
        self.publisher_ = self.create_publisher(Conversation, '/handler', 10)
        self.subscription = self.create_subscription(
            Conversation,
            '/handler',
            self.listener_callback,
            10)
        self.subscription  # evita o warning de variável não usada
        self.awaiting_final_instruction = True

    def listener_callback(self, msg):
        message = msg.message
        self.history = msg.history
        self.history.append(f'{message}')
        self.get_logger().info(f'Robo disse: "{message}"')
        
        # Processa as mensagens do robo
        if 'robo:' in message.lower():
            if any(keyword in message.lower() for keyword in ['100', '150', '200']):
                self.send_random_instruction()
            elif any(animal in message.lower() for animal in ['gato', 'cachorro', 'cavalo']):
                self.send_instruction('Retorne ao ponto de partida!')
            else:
                self.send_instruction('Não estou entendendo o que você está dizendo.')
                self.get_logger().info('Mensagem do robo não reconhecida.')

    def send_random_instruction(self):
        instruction = random.choice(['Vá pela direita!', 'Vá pela esquerda!'])
        self.send_instruction(instruction)

    def send_instruction(self, instruction):
        msg = Conversation()
        msg.message = f'Handler: {instruction}'
        msg.history = self.history
        self.publisher_.publish(msg)
        self.history.append(msg.message)
        self.get_logger().info(f'Publicou: "{instruction}"')

def main(args=None):
    rclpy.init(args=args)
    handler_node = HandlerNode()

    rclpy.spin(handler_node)

    handler_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
