import os
import numpy as np
import trimesh
import triangle

from autolab_core import RigidTransform, YamlConfig
from visualization import Visualizer3D as vis

class Packager(object):

    def __init__(self, config):
        """Create a packager with the given parameters.

        Parameters
        ----------
        config : autolab_core.YamlConfig
            A dict containing the parameters for the packager.

        Other Parameters
        ----------------
        min_border_width_pct : float
            The minimum border width as a percentage of the x extent of the object.
        max_border_width_pct : float
            The maximum border width as a percentage of the x extent of the object.
        min_tab_height_pct : float
            The minimum top tab height as a percentage of the y extent of the object.
        max_tab_height_pct : float
            The maximum top tab height as a percentage of the y extent of the object.
        min_depth : float
            The minimum depth of the cardboard backing.
        max_depth : float
            The maximum depth of the cardboard backing.
        offset : float
            The offset of the packaging from the object.
        """
        self._config = config

    def package(self, mesh):
        if not mesh.is_watertight:
            print mesh.metadata
            raise ValueError('Must have a watertight mesh to package it!')

        # Sample values
        border_width_pct = np.random.uniform(self._config['min_border_width_pct'],
                                             self._config['max_border_width_pct'])
        tab_height_pct = np.random.uniform(self._config['min_tab_height_pct'],
                                           self._config['max_tab_height_pct'])
        depth = np.random.uniform(self._config['min_depth'],
                                  self._config['max_depth'])
        offset = self._config['offset']
        ext_limits = np.array(self._config['ext_limits'])

        # Determine if the object is packable
        return self._package(mesh, border_width_pct, tab_height_pct, depth, offset, ext_limits)

    def _get_packaged_pose(self, mesh):
        # Make copy of argument
        mesh = mesh.copy()

        # Compute stable pose with least z-axis height
        tfs, _ = mesh.compute_stable_poses()
        min_z, min_tf = np.infty, None
        for tf in tfs:
            m = mesh.copy().apply_transform(tf)
            z_ext = m.extents[2]
            if z_ext < min_z:
                min_z = z_ext
                min_tf = tf

        # Put mesh in that stable pose
        mesh.apply_transform(min_tf)

        # Rotate the mesh about that stable pose, pick one that gives largest y extent
        theta = 0
        dtheta = 0.1
        min_rot = np.eye(4)
        min_x_ext = mesh.extents[0]
        while theta < np.pi:
            rot = np.eye(4)
            rot[:3,:3] = RigidTransform.z_axis_rotation(theta)
            m = mesh.copy()
            m.apply_transform(rot)
            x_ext = m.extents[0]
            if x_ext < min_x_ext:
                min_x_ext = x_ext
                min_rot = rot
            theta += dtheta

        return min_rot.dot(min_tf)

    def _package(self, mesh, border_width_pct, tab_height_pct, depth, offset, ext_limits):
        mesh = mesh.copy()

        pose = self._get_packaged_pose(mesh)
        mesh.apply_transform(pose)

        # Determine if mesh should be packaged based on extents
        extents = mesh.extents
        if np.any(extents > ext_limits):
            return None

        border_width = border_width_pct * mesh.extents[0]
        tab_height = tab_height_pct * mesh.extents[1]

        # Compute lower and upper bounds of the mesh in its stable pose
        bl, bu = mesh.bounds
        xl, xu = bl[0] - border_width, bu[0] + border_width
        yl, yu = bl[1] - border_width, bu[1] + border_width + tab_height
        zl, zu = -offset - depth, -offset

        # Find a triangle with a vertex touching the ground an a face pointing down.
        face_ind = None
        for i, tri in enumerate(mesh.triangles):
            if (np.abs(tri)[:,2] < 1e-12).any() and np.dot(mesh.face_normals[i], np.array([0.0, 0.0, -1.0])) > 0.0:
                face_ind = i
                break
        if face_ind is None:
            raise ValueError('Malformed mesh')

        # Create the extrusion
        vinds = mesh.faces[face_ind]
        vo = len(mesh.vertices)
        new_vertices = mesh.triangles[face_ind].copy()
        new_vertices[:,2] = np.array([zu, zu, zu])
        new_faces = np.array([
            [vinds[0], vinds[1], 1+vo],
            [vinds[0], 1+vo, 0+vo],
            [vinds[1], vinds[2], 2+vo],
            [vinds[1], 2+vo, 1+vo],
            [vinds[2], vinds[0], 0+vo],
            [vinds[2], 0+vo, 2+vo],
        ])

        verts = np.vstack((mesh.vertices, new_vertices))
        faces = np.vstack((mesh.faces, new_faces))
        faces = np.delete(faces, face_ind, 0)
        mesh = trimesh.Trimesh(verts, faces, process=False)

        # Now, create the base
        new_vertices = np.array([
            [xl, yl, zu],
            [xu, yl, zu],
            [xu, yu, zu],
            [xl, yu, zu],
            [xl, yl, zl],
            [xu, yl, zl],
            [xu, yu, zl],
            [xl, yu, zl],
        ])

        # Compute top faces using 2D Delaunay triangulation
        vo = len(mesh.vertices)
        vinds = np.array([vo - 3, vo - 2, vo - 1])
        orig_vertices = mesh.vertices[-3:]
        verts_2d = np.array([
            [xl, yl],
            [xu, yl],
            [xu, yu],
            [xl, yu],
            orig_vertices[0][:2],
            orig_vertices[1][:2],
            orig_vertices[2][:2]
        ])
        plsg = {
            'segments' : np.array([[5,4],[6,5],[4,6]]).astype(np.int32),
            'vertices' : verts_2d,
            'holes' : np.array(np.mean(verts_2d[4:],axis=0))
        }
        faces = triangle.triangulate(plsg, 'pc')['triangles']
        faces[faces == 4] = vinds[0] - vo
        faces[faces == 5] = vinds[1] - vo
        faces[faces == 6] = vinds[2] - vo
        faces = faces + vo

        # Create remainder of box
        new_faces = np.array([
            [0, 5, 1],
            [0, 4, 5],
            [1, 6, 2],
            [1, 5, 6],
            [2, 7, 3],
            [2, 6, 7],
            [3, 4, 0],
            [3, 7, 4],
            [4, 7, 5],
            [5, 7, 6]
        ]) + vo
        new_faces = np.vstack((faces, new_faces))

        verts = np.vstack((mesh.vertices, new_vertices))
        faces = np.vstack((mesh.faces, new_faces))
        mesh = trimesh.Trimesh(verts, faces, process=False)
        mesh.apply_translation(-mesh.center_mass)
        return mesh

if __name__ == '__main__':
    cfg = YamlConfig('cfg/tools/packager.yaml')
    p = Packager(cfg)

    if not os.path.exists(cfg['out_dir']):
        os.makedirs(cfg['out_dir'])

    for fn in os.listdir(cfg['in_dir']):
        full_fn = os.path.join(cfg['in_dir'], fn)
        fn = fn.split('.')[0]
        #exp_fn = os.path.join(cfg['out_dir'], '{}_packaged.obj'.format(fn))
        #os.rename(full_fn, exp_fn)
        m = trimesh.load_mesh(full_fn)
        m = p.package(m)
        if m is not None:
            if not m.is_watertight:
                continue
            bn, ext = os.path.splitext(fn)
            exp_fn = os.path.join(cfg['out_dir'], '{}_packaged.obj'.format(fn))
            m.export(exp_fn)
