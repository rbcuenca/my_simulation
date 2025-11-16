# orquestrador.py
import rclpy
import random
from rclpy.node import Node
from robcomp_interfaces.msg import MudaPista

class OrquestradorNode(Node):

    def __init__(self):
        super().__init__('orquestrador_node')

        self.robot_state = 'espera_ready'
        self.state_machine = {
            'espera_ready': self.espera_ready,
            'espera_tempo': self.espera_tempo,
            'manda_mudar': self.manda_mudar,
            'done': self.done,
        }

        self.recebeu_ready = False
        self.nome_aluno = ''
        self.time_to_next = None
        self.dt = 0.1

        self.controle_sub = self.create_subscription(
            MudaPista,
            '/controle',
            self.controle_callback,
            10
        )
        self.controle_pub = self.create_publisher(
            MudaPista,
            '/controle',
            10
        )

        self.timer = self.create_timer(self.dt, self.control)

    def controle_callback(self, msg: MudaPista):
        if msg.status == 'READY':
            self.recebeu_ready = True
            self.nome_aluno = msg.aluno

    def espera_ready(self):
        if self.recebeu_ready:
            self.get_logger().info(f'Robô READY de {self.nome_aluno}')
            self.recebeu_ready = False
            self.time_to_next = random.uniform(50.0, 80.0)
            self.robot_state = 'espera_tempo'

    def espera_tempo(self):
        if self.time_to_next is None:
            self.time_to_next = random.uniform(50.0, 80.0)

        self.time_to_next -= self.dt

        if self.time_to_next <= 0.0:
            self.robot_state = 'manda_mudar'

    def manda_mudar(self):
        msg = MudaPista()
        if random.choice([True, False]):
            msg.status = 'MUDAR_HORARIO'
        else:
            msg.status = 'MUDAR_ANTIHORARIO'

        msg.aluno = ''
        msg.timestamp = self.get_clock().now().to_msg()

        self.get_logger().info(f'Enviando comando aleatório: {msg.status}')
        self.controle_pub.publish(msg)

        # Agenda o próximo comando em 50-80 s
        self.time_to_next = random.uniform(50.0, 80.0)
        self.robot_state = 'espera_tempo'

    def done(self):
        pass

    def control(self):
        self.state_machine[self.robot_state]()

def main(args=None):
    rclpy.init(args=args)
    node = OrquestradorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
