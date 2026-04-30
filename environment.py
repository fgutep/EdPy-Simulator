"""Environment module for EdPy Robot Simulator.

Defines the simulation world with obstacles and lines for the robot to interact with.
"""

import math
from typing import List, Tuple, Optional


class Obstacle:
    """Base class for obstacles in the environment."""

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this obstacle."""
        raise NotImplementedError

    def distance_to_point(self, x: float, y: float) -> float:
        """Calculate distance from point to the nearest edge of this obstacle."""
        raise NotImplementedError

    def intersects_line(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if a line segment intersects this obstacle."""
        raise NotImplementedError


class RectObstacle(Obstacle):
    """Rectangular obstacle."""

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains_point(self, x: float, y: float) -> bool:
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def distance_to_point(self, x: float, y: float) -> float:
        # Find closest point on rectangle
        closest_x = max(self.x, min(x, self.x + self.width))
        closest_y = max(self.y, min(y, self.y + self.height))
        return math.sqrt((x - closest_x) ** 2 + (y - closest_y) ** 2)

    def intersects_line(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        # Check if either endpoint is inside
        if self.contains_point(x1, y1) or self.contains_point(x2, y2):
            return True

        # Check intersection with each edge
        edges = [
            (self.x, self.y, self.x + self.width, self.y),  # Top
            (self.x, self.y + self.height, self.x + self.width, self.y + self.height),  # Bottom
            (self.x, self.y, self.x, self.y + self.height),  # Left
            (self.x + self.width, self.y, self.x + self.width, self.y + self.height),  # Right
        ]

        for ex1, ey1, ex2, ey2 in edges:
            if self._lines_intersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2):
                return True

        return False

    @staticmethod
    def _lines_intersect(x1: float, y1: float, x2: float, y2: float,
                         x3: float, y3: float, x4: float, y4: float) -> bool:
        """Check if two line segments intersect."""
        def ccw(ax, ay, bx, by, cx, cy):
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

        return (ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4) and
                ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4))


class CircleObstacle(Obstacle):
    """Circular obstacle."""

    def __init__(self, x: float, y: float, radius: float):
        self.x = x
        self.y = y
        self.radius = radius

    def contains_point(self, x: float, y: float) -> bool:
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2) <= self.radius

    def distance_to_point(self, x: float, y: float) -> float:
        dist = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
        return max(0, dist - self.radius)

    def intersects_line(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        # Check if either endpoint is inside
        if self.contains_point(x1, y1) or self.contains_point(x2, y2):
            return True

        # Project circle center onto line segment
        dx = x2 - x1
        dy = y2 - y1
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            return self.distance_to_point(x1, y1) <= self.radius

        t = max(0, min(1, ((self.x - x1) * dx + (self.y - y1) * dy) / line_len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((self.x - proj_x) ** 2 + (self.y - proj_y) ** 2) <= self.radius


class LineSegment:
    """Line segment for line tracking sensor."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float,
                 color: str = "black", thickness: float = 5):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.thickness = thickness

    def distance_to_point(self, x: float, y: float) -> float:
        """Calculate perpendicular distance from point to line segment."""
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            return math.sqrt((x - self.x1) ** 2 + (y - self.y1) ** 2)

        t = max(0, min(1, ((x - self.x1) * dx + (y - self.y1) * dy) / line_len_sq))
        proj_x = self.x1 + t * dx
        proj_y = self.y1 + t * dy

        return math.sqrt((x - proj_x) ** 2 + (y - proj_y) ** 2)

    def is_point_on_line(self, x: float, y: float, threshold: float = 8) -> bool:
        """Check if point is on the line (within threshold distance)."""
        return self.distance_to_point(x, y) <= threshold


class Environment:
    """Simulation environment containing obstacles and lines."""

    def __init__(self, width: float = 800, height: float = 600):
        self.width = width
        self.height = height
        self.obstacles: List[Obstacle] = []
        self.lines: List[LineSegment] = []

    def add_obstacle(self, obstacle: Obstacle) -> None:
        """Add an obstacle to the environment."""
        self.obstacles.append(obstacle)

    def remove_obstacle_at(self, x: float, y: float) -> bool:
        """Remove obstacle at given point. Returns True if removed."""
        for i, obs in enumerate(self.obstacles):
            if obs.contains_point(x, y):
                del self.obstacles[i]
                return True
        return False

    def add_line(self, line: LineSegment) -> None:
        """Add a line segment to the environment."""
        self.lines.append(line)

    def clear(self) -> None:
        """Remove all obstacles and lines."""
        self.obstacles.clear()
        self.lines.clear()

    def check_collision(self, x: float, y: float) -> bool:
        """Check if point collides with any obstacle."""
        for obs in self.obstacles:
            if obs.contains_point(x, y):
                return True
        return False

    def get_obstacle_at(self, x: float, y: float) -> Optional[Obstacle]:
        """Get obstacle at given point, if any."""
        for obs in self.obstacles:
            if obs.contains_point(x, y):
                return obs
        return None

    def ray_cast(self, x: float, y: float, angle: float,
                 max_distance: float = 100) -> Tuple[Optional[Obstacle], float]:
        """Cast a ray and find the first obstacle it hits.

        Returns: (obstacle, distance) or (None, max_distance) if no hit.
        """
        rad = math.radians(angle)
        end_x = x + max_distance * math.cos(rad)
        end_y = y + max_distance * math.sin(rad)

        closest_obs = None
        closest_dist = max_distance

        for obs in self.obstacles:
            if obs.intersects_line(x, y, end_x, end_y):
                # Binary search to find approximate intersection distance
                dist = self._find_intersection_distance(x, y, end_x, end_y, obs)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_obs = obs

        return closest_obs, closest_dist

    def _find_intersection_distance(self, x1: float, y1: float,
                                    x2: float, y2: float,
                                    obstacle: Obstacle) -> float:
        """Find distance to intersection using binary search."""
        lo, hi = 0.0, 1.0
        for _ in range(10):  # 10 iterations for precision
            mid = (lo + hi) / 2
            mid_x = x1 + mid * (x2 - x1)
            mid_y = y1 + mid * (y2 - y1)
            if obstacle.contains_point(mid_x, mid_y):
                hi = mid
            else:
                lo = mid

        mid = (lo + hi) / 2
        mid_x = x1 + mid * (x2 - x1)
        mid_y = y1 + mid * (y2 - y1)
        return math.sqrt((mid_x - x1) ** 2 + (mid_y - y1) ** 2)

    def check_line_position(self, x: float, y: float) -> bool:
        """Check if point is on any line (True = on black line)."""
        for line in self.lines:
            if line.is_point_on_line(x, y):
                return True
        return False

    def create_default_environment(self) -> None:
        """Create a default environment with some obstacles and lines."""
        self.clear()

        # Add some rectangular obstacles
        self.add_obstacle(RectObstacle(100, 100, 50, 50))
        self.add_obstacle(RectObstacle(600, 400, 80, 60))
        self.add_obstacle(RectObstacle(300, 200, 40, 40))

        # Add a circular obstacle
        self.add_obstacle(CircleObstacle(500, 150, 30))

        # Add some lines for line tracking
        self.add_line(LineSegment(50, 300, 750, 300, color="black", thickness=8))
        self.add_line(LineSegment(400, 50, 400, 550, color="black", thickness=8))
