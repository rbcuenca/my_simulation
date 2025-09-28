import rclpy
import math
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from rclpy.duration import Duration
from robcomp_util.odom import Odom
from robcomp_interfaces.msg import OrquestratorMSG

# --------------------------------------------------

class Orchestrator(Node, Odom):

    def __init__(self):
        super().__init__('orchestrator_showbot_node')
        Odom.__init__(self)
        rclpy.spin_once(self)

        # Pub/Sub do barramento ShowBot
        self.show_pub = self.create_publisher(OrquestratorMSG, '/showbot', 10)
        self.show_sub = self.create_subscription(
            OrquestratorMSG,
            '/showbot',
            self.showbot_cb,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        )

        # Estados
        self.robot_state = 'aguarda_ready'
        self.temp_state = None
        self.state_machine = {
            'aguarda_ready': self.aguarda_ready,
            'envia_in_progress': self.envia_in_progress,
            'aguarda_done': self.aguarda_done,
            'envia_feedback': self.envia_feedback,
            'erro': self.erro,
            'fim': self.fim,
        }

        # Fila de comandos (ex.: duas formas)
        # Ajuste como quiser; pode repetir, randomizar, etc.
        self.command_queue = [
            {'side': 0.8, 'angle_deg': 90},
            {'side': 0.6, 'angle_deg': 60},
        ]

        # Controle interno
        self.started = False
        self.last_error_pub = None  # para throttling de ERROR (1 Hz)
        self.timebox_deadline = None
        self.current_cmd = None

        # Pose inicial para calcular deriva
        self.x0 = None
        self.y0 = None

        # Info do aluno (pega do READY)
        self.student_name = ""
        self.horario_ready = 0.0

        # Timer principal (NÃO usar sleeps/loops infinitos)
        self.timer = self.create_timer(0.1, self.control)
        rclpy.spin_once(self, timeout_sec=0.0)

        self.get_logger().info("Orchestrator iniciado. Aguardando READY...")

    # Utilitário: horário float64 (seg)
    def _now_float(self) -> float:
        t = self.get_clock().now().to_msg()
        return float(t.sec) + float(t.nanosec) * 1e-9

    # Publica OrquestratorMSG
    def _publish(self, *, status: str, side: float = 0.0, angle_deg: int = 0, drift_m: float = 0.0):
        msg = OrquestratorMSG()
        msg.student_name = self.student_name or "N/A"
        msg.horario = self._now_float()
        msg.status = status
        msg.side = float(side)
        msg.angle_deg = int(angle_deg)
        msg.drift_m = float(drift_m)
        self.show_pub.publish(msg)

    # --------------------------------------------------
    # Callback do barramento OrquestratorMSG
    def showbot_cb(self, msg: OrquestratorMSG):
        # Guarda nome/horário do READY
        if msg.status.strip().upper() == "READY":
            self.student_name = msg.student_name
            self.horario_ready = msg.horario
            # Se estávamos em erro, READY libera a retomada
            if self.robot_state == 'erro':
                self.get_logger().info("READY recebido após ERROR; retomando sequência.")
                self.robot_state = 'envia_in_progress'
            elif self.robot_state == 'aguarda_ready':
                # fluxo normal
                self.robot_state = 'envia_in_progress'

        elif msg.status.strip().upper() == "DONE":
            # DONE recebido: pronto para calcular deriva e enviar FEEDBACK
            if self.robot_state == 'aguarda_done':
                self.robot_state = 'envia_feedback'

        elif msg.status.strip().upper() == "IN_PROGRESS":
            # Normalmente será nossa própria msg vista no echo; ignoramos
            pass

        elif msg.status.strip().upper() == "FEEDBACK":
            # Normalmente FEEDBACK é do Orchestrator; se ecoar, ignorar
            pass

        elif msg.status.strip().upper() == "ERROR":
            # Se o robô publicar ERROR (raro), tratamos como um pedido de retry
            self.get_logger().warn("Robô publicou ERROR; aguardando READY.")
            self.robot_state = 'aguarda_ready'

    # --------------------------------------------------
    # Estados da máquina

    def aguarda_ready(self):
        # Apenas espera; transição é disparada pelo callback (READY -> envia_in_progress)
        pass

    def envia_in_progress(self):
        if not self.command_queue:
            self.get_logger().info("Fila de comandos vazia. Encerrando orquestração.")
            self.robot_state = 'fim'
            return

        # Pega próximo comando
        self.current_cmd = self.command_queue.pop(0)
        side = float(self.current_cmd['side'])
        angle_deg = int(self.current_cmd['angle_deg'])

        # Marca pose inicial e timebox de 4 min
        self.x0, self.y0 = float(self.x), float(self.y)
        self.timebox_deadline = self.get_clock().now() + Duration(seconds=240.0) # 4 minutos

        self.get_logger().info(
            f"Enviando IN_PROGRESS: L={side:.2f} m, θ={angle_deg}°. Pose inicial=({self.x0:.3f},{self.y0:.3f})"
        )
        self._publish(status="IN_PROGRESS", side=side, angle_deg=angle_deg)
        self.robot_state = 'aguarda_done'

    def aguarda_done(self):
        # Verifica timebox
        if self.timebox_deadline and self.get_clock().now() >= self.timebox_deadline:
            self.get_logger().warn("Estouro de 2 minutos para a forma. Entrando em estado de erro.")
            self.robot_state = 'erro'

    def envia_feedback(self):
        # Calcula drift
        if self.x0 is None or self.y0 is None:
            drift = 999.0  # caso defensivo
        else:
            dx = float(self.x) - self.x0
            dy = float(self.y) - self.y0
            drift = math.hypot(dx, dy)

        self.get_logger().info(f"Enviando FEEDBACK: drift_m={drift:.3f} m")
        self._publish(status="FEEDBACK", drift_m=drift)

        # Limpa estado da forma e volta a aguardar próximo READY
        self.x0 = self.y0 = None
        self.timebox_deadline = None
        self.current_cmd = None
        self.robot_state = 'aguarda_ready'

    def erro(self):
        # Publica ERROR a 1 Hz até receber READY (callback muda o estado)
        now = self.get_clock().now()
        if self.last_error_pub is None or (now - self.last_error_pub) >= Duration(seconds=1.0):
            self.get_logger().warn("Publicando ERROR (timeout). Aguardando READY do robô na origem.")
            self._publish(status="ERROR")
            self.last_error_pub = now

    def fim(self):
        # Nada a fazer; o main encerra quando quiser
        pass

    # --------------------------------------------------
    # Loop de controle (timer)
    def control(self):
        self.get_logger().info(f"Estado Atual: {self.robot_state}")
        self.state_machine[self.robot_state]()

# --------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    ros_node = Orchestrator()

    # Mantém rodando até o usuário encerrar (ou você pode decidir parar ao fim)
    try:
        while rclpy.ok():
            rclpy.spin_once(ros_node)
            if ros_node.robot_state == 'fim':
                break
    finally:
        ros_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
