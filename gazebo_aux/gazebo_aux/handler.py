import rclpy
from rclpy.node import Node
from robcomp_interfaces.msg import Conversation
import random

class HandlerNode(Node):

    def __init__(self):
        super().__init__('handler_node')
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
        self.history.append(f'Robo: {message}')
        self.get_logger().info(f'Robo disse: "{message}"')
        
        # Processa as mensagens do robo
        if 'Estou pronto para explorar' in message:
            self.send_random_instruction()
        elif 'Estou bloqueado' in message:
            self.send_instruction('Retorne rapidamente!')
        elif 'Cheguei' in message:
            self.get_logger().info('Robo informou que chegou ao destino final.')
            self.awaiting_final_instruction = True
        else:
            self.get_logger().info('Mensagem do robo não reconhecida.')

    def send_random_instruction(self):
        # Define aleatoriamente a próxima instrução
        if self.awaiting_final_instruction:
            instruction = random.choice(['Vá por cima!', 'Vá por baixo!', 'Aguarde mais um momento.'])
            self.send_instruction(instruction)
            if instruction != 'Aguarde mais um momento.':
                self.awaiting_final_instruction = False
        else:
            self.get_logger().info('Robô já está em execução, aguardando o próximo comando.')

    def send_instruction(self, instruction):
        msg = Conversation()
        msg.message = f'Handler: {instruction}'
        msg.history = self.history
        self.publisher_.publish(msg)
        self.history.append(f'Handler: {instruction}')
        self.get_logger().info(f'Publicou: "{instruction}"')

        # Se a instrução for "Aguarde mais um momento.", continuar aguardando
        if instruction == 'Aguarde mais um momento.':
            self.get_logger().info('Aguardando... enviando nova instrução em breve.')
            self.send_random_instruction()  # Gera uma nova instrução aleatória até dar uma final

def main(args=None):
    rclpy.init(args=args)
    handler_node = HandlerNode()

    rclpy.spin(handler_node)

    handler_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
