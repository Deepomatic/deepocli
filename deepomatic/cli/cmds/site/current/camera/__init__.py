from ....utils import Command
from deepomatic.cli.lib.camera import get_camera_ctrl


class _CameraServerCommand(Command):
    """
        Base class for commands that calls the camera server
    """

    def run(self, camera_server_address, **args):
        self.manager = get_camera_ctrl(camera_server_address)

    def print_camera(self, camera):
        print("camera: {}".format(camera['name']))
        for key, value in camera.items():
            if key != "name":
                print("\t{}: {}".format(key, value))


class _CameraCommand(_CameraServerCommand):
    """
        Base class for commands that requires the camera's name
    """

    def setup(self, subparsers):
        parser = super(_CameraCommand, self).setup(subparsers)
        parser.add_argument('name', type=str, help="camera name")
        return parser


class CameraCommand(Command):
    """
        Control the Camera server
    """

    def setup(self, subparsers):
        parser = super(CameraCommand, self).setup(subparsers)
        parser.add_argument('--camera_server_address', required=True, type=str, help="camera server address")
        return parser

    class AddCommand(_CameraServerCommand):
        """
            Add a camera
        """

        def setup(self, subparsers):
            parser = super(CameraCommand.AddCommand, self).setup(subparsers)
            parser.add_argument('name', type=str, help="camera name")
            parser.add_argument('address', type=str, help="camera address")
            parser.add_argument('--fps', type=float, help="camera fps", default=None)

            group = parser.add_mutually_exclusive_group()
            group.add_argument("--tcp", action="store_true")
            group.add_argument("--udp", action="store_true")

            return parser

        def run(self, name, address, fps, tcp, udp, **kwargs):
            super(CameraCommand.AddCommand, self).run(**kwargs)
            added = self.manager.add(name, address, fps, tcp)
            self.print_camera(added)

    class RemoveCommand(_CameraCommand):
        """
            Remove a camera
        """

        def run(self, name, **kwargs):
            super(CameraCommand.RemoveCommand, self).run(**kwargs)
            self.manager.delete(name)

    class StartCommand(_CameraCommand):
        """
            Start a camera
        """

        def run(self, name, **kwargs):
            super(CameraCommand.StartCommand, self).run(**kwargs)
            self.manager.start(name)

    class StopCommand(_CameraCommand):
        """
            Stop a camera
        """

        def run(self, name, **kwargs):
            super(CameraCommand.StopCommand, self).run(**kwargs)
            self.manager.stop(name)

    class StatusCommand(_CameraCommand):
        """
            Get a camera's status
        """

        def run(self, name, **kwargs):
            super(CameraCommand.StatusCommand, self).run(**kwargs)
            status = self.manager.get(name)
            self.print_camera(status)

    class ListCommand(_CameraServerCommand):
        """
            List the cameras
        """

        def run(self, **kwargs):
            super(CameraCommand.ListCommand, self).run(**kwargs)
            cameras = self.manager.list()
            print("Cameras:")
            for camera in cameras:
                self.print_camera(camera)
