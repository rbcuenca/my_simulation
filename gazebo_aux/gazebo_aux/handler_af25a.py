import random
from robcomp_interfaces.msg import HandlerAF25a
import rclpy
from rclpy.node import Node


class HandlerAF25aNode(Node):

    START       = 'START'
    IN_PROGRESS = 'IN_PROGRESS'
    APPROACHING = 'APPROACHING'
    STOP      = 'STOP'

    def __init__(self):
        super().__init__('handler_af25a')

        self.pub = self.create_publisher(HandlerAF25a, '/handler_af_25a', 10)
        self.sub = self.create_subscription(
            HandlerAF25a, '/handler_af_25a', self.handler_callback, 10
        )

        self.random_max = 30
        self.state = 'waiting'

        self.timer = self.create_timer(1.0, self.periodic)

    def handler_callback(self, msg: HandlerAF25a):
        print(f'Recebido: {msg.status} - {msg.command}')
        if msg.command not in ['Iniciando', 'alterne', '']:
            self.get_logger().warn(f'\n\n\nComando desconhecido: {msg.command}')
            self.get_logger().warn(f'Apenas o Handler deve enviar comandos!!!\n\n\n')
            return
        if msg.status == self.START and self.state == 'waiting':
            self.get_logger().info('\nSTART recebido; enviando IN_PROGRESS')
            self.state = 'running'
            self.value = random.randint(0, self.random_max)
            self._send(status=self.IN_PROGRESS, command='Iniciando')

        elif msg.status == self.APPROACHING:
            if msg.response == '':
                self.get_logger().info(f'\nRobô não informou o bloco ao qual está indo!!!')
            else:
                self.get_logger().info(f'\nRobô indo ao bloco {msg.response}')
                self.state = 'approaching'

        elif msg.status == self.IN_PROGRESS and msg.command != 'alterne':
            self.get_logger().info('\nRobô andando..')
            self.value = random.randint(0, self.random_max)
            self.state = 'running'
        
        elif msg.status == self.STOP:
            self.state = 'waiting'

    def periodic(self):
        print("Estado atual:", self.state)
        if self.state == 'running':
            if random.randint(0, self.random_max) == self.value:
                self.get_logger().info('\nEnviando comando alterne')
                self._send(status=self.IN_PROGRESS, command='alterne')
                self.state = 'waiting_approach'

    def _send(self, *, status: str, command: str):
        msg = HandlerAF25a()
        msg.status = status
        msg.command = command
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = HandlerAF25aNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()