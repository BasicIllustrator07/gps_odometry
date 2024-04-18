#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Pose
from geometry_msgs.msg import QuaternionStamped

import math
import utm
import numpy as np


class GPS_TO_ODOM(Node):
    def __init__(self):
        super().__init__('gps_to_odom')

        self.gnss_subscriber=self.create_subscription(NavSatFix,'/gnss',self.gnss_callback,10)
        self.imu_subscriber=self.create_subscription(QuaternionStamped,'/filter/quaternion',self.imu_callback,10)

        self.odom_publisher=self.create_publisher(Odometry,'/odometry/gps',10)

        self.rotation=None

        self.x_prev=0
        self.y_prev=0

        self.x_now=0
        self.y_now=0
        
        self.initial_yaw=0.0

        self.i=0
        self.j=0

        self.initial_utm=None

    def gnss_callback(self,gnss):
        latitude=gnss.latitude
        longitude=gnss.longitude

        if self.j==0:
            self.initial_utm=utm.from_latlon(latitude,longitude)
            self.j=1

        
        self.utm=utm.from_latlon(latitude,longitude)

        odom=Odometry()
        pose=Pose()

        if(gnss.position_covariance[0]<1.0 and gnss.position_covariance[4]<1.0 and self.i==1):
            coordinates=self.pose()
            x=coordinates[0]
            y=coordinates[1]

            print(coordinates)

            pose.position.x=x
            pose.position.y=y
            odom.pose.pose=pose

            odom.pose.covariance[0]=(self.rotation @ np.array([[gnss.position_covariance[0],0.0],[0.0,gnss.position_covariance[4]]]) @ self.rotation.T)[0,0]
            odom.pose.covariance[7]=(self.rotation @ np.array([[gnss.position_covariance[0],0.0],[0.0,gnss.position_covariance[4]]]) @ self.rotation.T)[1,1]


            odom.child_frame_id="imu_link"
            odom.header.frame_id="odom"
            self.odom_publisher.publish(odom)

    def imu_callback(self,orientation):
        w=orientation.quaternion.w
        x=orientation.quaternion.x
        y=orientation.quaternion.y
        z=orientation.quaternion.z
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = w * w + x * x - y * y - z * z

        if self.i==0:
            self.initial_yaw=math.atan2(siny_cosp, cosy_cosp)
            self.rotation=np.array([[np.cos(self.initial_yaw), -np.sin(self.initial_yaw)], [np.sin(self.initial_yaw), np.cos(self.initial_yaw)]])
            self.i=1

    def pose(self):
        initial_coordinates = self.rotation @ np.array([[self.initial_utm[0]],[self.initial_utm[1]]])

        temp_coordinates = self.rotation @ np.array([[self.utm[0]],[self.utm[1]]])

        self.x_now = (temp_coordinates-initial_coordinates)[0,0]
        self.y_now = (temp_coordinates-initial_coordinates)[1,0]

        x=0.5*self.x_now+0.5*self.y_now
        y=0.5*self.x_now+0.5*self.y_now

        self.x_prev=self.x_now
        self.y_prev=self.y_now

        coordinates = [x,y]
        return coordinates



def main(args=None):
    rclpy.init(args=args)

    gps_odom_publisher=GPS_TO_ODOM()
    rclpy.spin(gps_odom_publisher)

    gps_odom_publisher.destroy_node()
    rclpy.shutdown()

if __name__=='__main__':
    main()