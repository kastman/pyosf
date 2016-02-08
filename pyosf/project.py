"""These are the main classes to be used by external scripts/apps
"""

import os
import sys
try:
    from psychopy import logging
except:
    import logging
from pyosf import remote, local, sync
import json

PY3 = sys.version_info > (3,)


class Project(object):
    """Stores the project information for synchronization.

    Stores the id and username for the remote.Project on OSF, the location of
    the local files, and a record of the index at the point of previous sync

    Parameters
    ----------

    project_file : str
        Location of the project file with info

    root_path : str
        The root of the folder where the local files are situated

    osf : pyosf.remote.OSFProject instance)
        The remote project that will be synchronised.

    """
    def __init__(self, project_file=None, root_path=None, osf=None):
        self.project_file = project_file
        self.root_path = root_path  # overwrite previous (indexed) location
        self.osf = osf  # not needed if project_file exists
        # load the project file (if exists) for info about previous sync
        index, username, project_id, root_path = self.load(project_file)
        self.index = index or []
        self.username = username

        # check/set root_path
        if self.root_path is None:
            self.root_path = root_path  # use what we just loaded
        elif root_path != self.root_path:
            logging.warn("The requested root_path and the previous root_path "
                         "differ. Using the requested path.")
        if self.root_path is None:
            raise AttributeError("Project file failed to load a root_path "
                                 "for the local files and none was provided")
        else:
            self.local = local.LocalFiles(self.root_path)

        # check/set remote session
        if osf is None:
            if username is None:
                raise AttributeError("No osf project was provided but also "
                                     "no username or authentication token")
            else:  # we have no remote but a username so try a remote.Session
                session = remote.Session(username)
                if project_id is None:
                    raise AttributeError("No project id was available. "
                                         "Project needs OSFProject or a "
                                         "previous project_file")
                else:
                    self.osf = remote.OSFProject(session=session,
                                                 id=project_id)
        else:
            self.osf = osf

    def __repr__(self):
        return "Project({})".format(self.project_file)

    def save(self, proj_path=None):
        """Save the project to a json-format file

        The info will be:
            - the `username` (so `remote.Project` can fetch an auth token)
            - the project id
            - the `root_path`
            - the current files `index`

        Parameters
        ----------

        proj_path : str
            Not needed unless saving to a new location.

        """
        if proj_path is None:
            proj_path = self.project_file
        if not os.path.isdir(os.path.dirname(proj_path)):
            os.makedirs(os.path.dirname(proj_path))
        if not os.path.isfile(proj_path):
            logging.info("Creating new Project file: {}".format(proj_path))
        # create the fields to save
        d = {}
        d['root_path'] = self.root_path
        d['username'] = self.osf.session.username
        d['project_id'] = self.osf.id
        d['index'] = self.index
        # do the actual file save
        print("saving to: {}".format(proj_path))
        with open(proj_path, 'wb') as f:
            json_str = json.dumps(d, indent=2)
            if PY3:
                f.write(bytes(json_str, 'UTF-8'))
            else:
                f.write(json_str)

    def load(self, proj_path=None):
        """Load the project from a json-format file

        The info will be:
            - the `username` (so `remote.Project` can fetch an auth token)
            - the project id the `root_path`
            - the current files `index`

        Parameters
        ----------

        proj_path : str
            Not needed unless saving to a new location.

        Returns
        ----------

        tuple (last_index, username, project_id, root_path)

        """
        if proj_path is None:
            proj_path = self.project_file
        if not os.path.isfile(proj_path):
            print('no file:{}'.format(os.path.abspath(proj_path)))
            return (None, None, None, None)
        else:
            with open(proj_path, 'r') as f:
                d = json.load(f)
            username = d['username']
            index = d['index']
            project_id = d['project_id']
            root_path = d['root_path']
        return index, username, project_id, root_path

    def get_changes(self):
        """Return the changes to be applied
        """
        osf_index = self.osf.create_index()
        local_index = self.local.create_index()
        changes = sync.get_changes(local_index, osf_index, self.index)
        return changes
