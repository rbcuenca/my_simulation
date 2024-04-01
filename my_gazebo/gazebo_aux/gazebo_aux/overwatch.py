import rclpy
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import os

# publish to watcher on terminal
# ros2 topic pub /watcher std_msgs/msg/String "data: 'start'"

class OverWatch(Node):

    def __init__(self):
        super().__init__('watcher_node') # Mude o nome do nó
        self.start_position_dict = {
            'position_1' : (-3, 0.1),
            'position_2' : (3, 0.1),
        }
        self.end_position_dict = {
            'position_1' : (-3, -3),
            'position_2' : (-3, 3),
        }

        # Inicialização de variáveis
        
        # Subscribers
        ## Coloque aqui os subscribers
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT))
        self.watcher_sub = self.create_subscription(
            String,
            '/watcher',
            self.watcher_callback,
            QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT))
        
        self.state_running = False

        # Publishers
        ## Coloque aqui os publishers
    
    def odom_callback(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

        # print(f'x: {self.x}, y: {self.y}')
    
    def distance(self, x1, y1, x2, y2):
        return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

    def check_start_position(self):
        if self.distance(self.x, self.y, self.start_position_dict['position_1'][0], self.start_position_dict['position_1'][1]) < 0.5:
            return 'position_1'
        elif self.distance(self.x, self.y, self.start_position_dict['position_2'][0], self.start_position_dict['position_2'][1]) < 0.5:
            return 'position_2'
        else:
            return None
    
    def check_arrival(self):
        if self.start_position == 'position_1':
            dist_y = self.end_position_dict['position_1'][1] - self.y
            print(dist_y)
            return dist_y > -0.4
        elif self.start_position == 'position_2':
            dist_y = self.y - self.end_position_dict['position_2'][1]
            print(dist_y)
            return dist_y > -0.3

    def watcher_callback(self, msg):
        if not self.state_running:
            if msg.data == 'start':
                self.start_time = self.get_clock().now()
                self.start_position = self.check_start_position()
                self.get_logger().info(f'Watcher started - at {self.start_position}')
                self.state_running = True
        else:
            if msg.data == 'stop':
                if self.check_arrival():
                    self.end_time = self.get_clock().now()
                    run_time = self.end_time - self.start_time
                    # run_time as MM:SS
                    run_time = run_time.nanoseconds / 1e9
                    run_time = f'{int(run_time/60)}:{int(run_time%60)}'
                    self.get_logger().info(f'Watcher stopped - run time: {run_time}')

                    # write to file in the HOME directory named AI_RUNTIME.txt
                    
                    file_path = os.path.expanduser('~//AI_RUNTIME.txt')


                    with open(file_path, 'a') as f:
                        f.write(f'{self.start_position} - Run Time: {run_time}\n')
                    self.state_running = False
                else:
                    self.get_logger().info('Did not reach the end position')
        
            
def main(args=None):
    rclpy.init(args=args)
    ros_node = OverWatch() # Mude o nome da classe

    rclpy.spin(ros_node)

    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()