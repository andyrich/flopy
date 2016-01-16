"""
mfdis module.  Contains the ModflowDis class. Note that the user can access
the ModflowDis class as `flopy.modflow.ModflowDis`.

Additional information for this MODFLOW package can be found at the `Online
MODFLOW Guide
<http://water.usgs.gov/ogw/modflow/MODFLOW-2005-Guide/index.html?dis.htm>`_.

"""

import sys
import numpy as np
from ..pakbase import Package
from ..utils import Util2d, Util3d, reference


ITMUNI = {"u":0,"s":1,"m":2,"h":3,"d":4,"y":5}
LENUNI = {"u":0,"f":1,"m":2,"c":3}

class ModflowDis(Package):
    """
    MODFLOW Discretization Package Class.

    Parameters
    ----------
    model : model object
        The model object (of type :class:`flopy.modflow.Modflow`) to which
        this package will be added.
    nlay : int
        Number of model layers (the default is 1).
    nrow : int
        Number of model rows (the default is 2).
    ncol : int
        Number of model columns (the default is 2).
    nper : int
        Number of model stress periods (the default is 1).
    delr : float or array of floats (ncol), optional
        An array of spacings along a row (the default is 1.0).
    delc : float or array of floats (nrow), optional
        An array of spacings along a column (the default is 0.0).
    laycbd : int or array of ints (nlay), optional
        An array of flags indicating whether or not a layer has a Quasi-3D
        confining bed below it. 0 indicates no confining bed, and not zero
        indicates a confining bed. LAYCBD for the bottom layer must be 0. (the
        default is 0)
    top : float or array of floats (nrow, ncol), optional
        An array of the top elevation of layer 1. For the common situation in
        which the top layer represents a water-table aquifer, it may be
        reasonable to set Top equal to land-surface elevation (the default is
        1.0)
    botm : float or array of floats (nlay, nrow, ncol), optional
        An array of the bottom elevation for each model cell (the default is
        0.)
    perlen : float or array of floats (nper)
        An array of the stress period lengths.
    nstp : int or array of ints (nper)
        Number of time steps in each stress period (default is 1).
    tsmult : float or array of floats (nper)
        Time step multiplier (default is 1.0).
    steady : boolean or array of boolean (nper)
        true or False indicating whether or not stress period is steady state
        (default is True).
    itmuni : int
        Time units, default is days (4)
    lenuni : int
        Length units, default is meters (2)
    extension : string
        Filename extension (default is 'dis')
    unitnumber : int
        File unit number (default is 11).
    xul : float
        x coordinate of upper left corner of the grid, default is None
    yul : float
        y coordinate of upper left corner of the grid, default is None
    rotation : float
        clockwise rotation (in degrees) of the grid about the upper left
        corner. default is 0.0
    proj4_str : str
        PROJ4 string that defines the xul-yul coordinate system
        (.e.g. '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ').
        Can be an EPSG code (e.g. 'EPSG:4326'). Default is 'EPSG:4326'
    start_dateteim : str
        starting datetime of the simulation. default is '1/1/1970'

    Attributes
    ----------
    heading : str
        Text string written to top of package input file.

    Methods
    -------

    See Also
    --------

    Notes
    -----

    Examples
    --------

    >>> import flopy
    >>> m = flopy.modflow.Modflow()
    >>> dis = flopy.modflow.ModflowDis(m)

    """

    def __init__(self, model, nlay=1, nrow=2, ncol=2, nper=1, delr=1.0,
                 delc=1.0, laycbd=0, top=1, botm=0, perlen=1, nstp=1,
                 tsmult=1, steady=True, itmuni=4, lenuni=2, extension='dis',
                 unitnumber=11, xul=None, yul=None, rotation=0.0,
                 proj4_str="EPSG:4326", start_datetime="1/1/1970"):

        # Call ancestor's init to set self.parent, extension, name and unit
        # number
        Package.__init__(self, model, extension, 'DIS', unitnumber)
        self.url = 'dis.htm'
        self.nrow = nrow
        self.ncol = ncol
        self.nlay = nlay
        self.nper = nper

        # Set values of all parameters
        self.heading = '# Discretization file for MODFLOW, generated by Flopy.'
        self.laycbd = Util2d(model, (self.nlay,), np.int, laycbd,
                              name='laycbd')
        self.laycbd[-1] = 0  # bottom layer must be zero
        self.delr = Util2d(model, (self.ncol,), np.float32, delr, name='delr',
                            locat=self.unit_number[0])
        self.delc = Util2d(model, (self.nrow,), np.float32, delc, name='delc',
                            locat=self.unit_number[0])
        self.top = Util2d(model, (self.nrow, self.ncol), np.float32,
                           top, name='model_top', locat=self.unit_number[0])
        self.botm = Util3d(model, (self.nlay + sum(self.laycbd),
                                    self.nrow, self.ncol), np.float32, botm,
                            'botm', locat=self.unit_number[0])
        self.perlen = Util2d(model, (self.nper,), np.float32, perlen,
                              name='perlen')
        self.nstp = Util2d(model, (self.nper,), np.int, nstp, name='nstp')
        self.tsmult = Util2d(model, (self.nper,), np.float32, tsmult,
                              name='tsmult')
        self.steady = Util2d(model, (self.nper,), np.bool,
                              steady, name='steady')

        try:
            self.itmuni = int(itmuni)
        except:
            self.itmuni = ITMUNI[itmuni.lower()[0]]
        try:
            self.lenuni = int(lenuni)
        except:
            self.lenuni = LENUNI[lenuni.lower()[0]]

        self.parent.add_package(self)
        self.itmuni_dict = {0: "undefined", 1: "seconds", 2: "minutes",
                            3: "hours", 4: "days", 5: "years"}

        self.sr = reference.SpatialReference(self.delr.array, self.delc.array,
                                             self.lenuni,xul=xul, yul=yul,
                                             rotation=rotation,
                                             proj4_str=proj4_str)
        self.start_datetime = start_datetime
        # calculate layer thicknesses
        self.__calculate_thickness()

    def checklayerthickness(self):
        """
        Check layer thickness.

        """
        return (self.thickness > 0).all()

    def get_cell_volumes(self):
        """
        Get an array of cell volumes.

        Returns
        -------
        vol : array of floats (nlay, nrow, ncol)

        """
        vol = np.empty((self.nlay, self.nrow, self.ncol))
        for l in range(self.nlay):
            vol[l, :, :] *= self.thickness.array[l]
        for r in range(self.nrow):
            vol[:, r, :] *= self.delc[r]
        for c in range(self.ncol):
            vol[:, :, c] *= self.delr[c]
        return vol

    @property
    def zcentroids(self):
        z = np.empty((self.nlay, self.nrow, self.ncol))
        z[0,:,:] = (self.top[:, :] + self.botm[0, :, :]) / 2.

        for l in range(1,self.nlay):
            z[l, :, :] = (self.botm[l - 1, :, :] + self.botm[l, :, :]) / 2.
        return z


    def get_node_coordinates(self):
        """
        Get y, x, and z cell centroids.

        Returns
        -------
        y : list of cell y-centroids

        x : list of cell x-centroids

        z : array of floats (nlay, nrow, ncol)
        """
        # In row direction
        y = np.empty((self.nrow))
        for r in range(self.nrow):
            if (r == 0):
                y[r] = self.delc[r] / 2.
            else:
                y[r] = y[r - 1] + (self.delc[r] + self.delc[r - 1]) / 2.
        # Invert y to convert to a cartesian coordiante system
        y = y[::-1]
        # In column direction
        x = np.empty((self.ncol))
        for c in range(self.ncol):
            if (c == 0):
                x[c] = self.delr[c] / 2.
            else:
                x[c] = x[c - 1] + (self.delr[c] + self.delr[c - 1]) / 2.
        # In layer direction
        z = np.empty((self.nlay, self.nrow, self.ncol))
        for l in range(self.nlay):
            if (l == 0):
                z[l, :, :] = (self.top[:, :] + self.botm[l, :, :]) / 2.
            else:
                z[l, :, :] = (self.botm[l - 1, :, :] + self.botm[l, :, :]) / 2.
        return y, x, z

    def get_lrc(self, nodes):
        """
        Get layer, row, column from a list of MODFLOW node numbers.

        Returns
        -------
        v : list of tuples containing the layer (k), row (i), 
            and column (j) for each node in the input list
        """
        if not isinstance(nodes, list):
            nodes = [nodes]
        nrc = self.nrow * self.ncol
        v = []
        for node in nodes:
            k = int(node / nrc)
            if ( k * nrc ) < node:
                k += 1
            ij = int(node - ( k - 1 ) * nrc)
            i = int(ij / self.ncol)
            if ( i * self.ncol ) < ij:
                i += 1
            j = ij - ( i - 1 ) * self.ncol
            v.append((k, i, j))
        return v

    def get_node(self, lrc_list):
        """
        Get node number from a list of MODFLOW layer, row, column tuples.

        Returns
        -------
        v : list of MODFLOW nodes for each layer (k), row (i), 
            and column (j) tuple in the input list
        """
        if not isinstance(lrc_list, list):
            lrc_list = [lrc_list]
        nrc = self.nrow * self.ncol
        v = []
        for [k, i, j] in lrc_list:
            node = int(( ( k - 1 ) * nrc ) + ( ( i - 1 ) * self.ncol ) + j)
            v.append(node)
        return v

    def read_from_cnf(self, cnf_file_name, n_per_line=0):
        """
        Read discretization information from an MT3D configuration file.

        """

        def getn(ii, jj):
            if (jj == 0):
                n = 1
            else:
                n = int(ii / jj)
                if (ii % jj != 0):
                    n = n + 1

            return n

        try:
            f_cnf = open(cnf_file_name, 'r')

            # nlay, nrow, ncol
            line = f_cnf.readline()
            s = line.split()
            cnf_nlay = int(s[0])
            cnf_nrow = int(s[1])
            cnf_ncol = int(s[2])

            # ncol column widths delr[c]
            line = ''
            for dummy in range(getn(cnf_ncol, n_per_line)):
                line = line + f_cnf.readline()
            cnf_delr = [float(s) for s in line.split()]

            # nrow row widths delc[r]
            line = ''
            for dummy in range(getn(cnf_nrow, n_per_line)):
                line = line + f_cnf.readline()
            cnf_delc = [float(s) for s in line.split()]

            # nrow * ncol htop[r, c]
            line = ''
            for dummy in range(getn(cnf_nrow * cnf_ncol, n_per_line)):
                line = line + f_cnf.readline()
            cnf_top = [float(s) for s in line.split()]
            cnf_top = np.reshape(cnf_top, (cnf_nrow, cnf_ncol))

            # nlay * nrow * ncol layer thickness dz[l, r, c]
            line = ''
            for dummy in range(getn(cnf_nlay * cnf_nrow * cnf_ncol, n_per_line)):
                line = line + f_cnf.readline()
            cnf_dz = [float(s) for s in line.split()]
            cnf_dz = np.reshape(cnf_dz, (cnf_nlay, cnf_nrow, cnf_ncol))

            # cinact, cdry, not used here so commented
            '''line = f_cnf.readline()
            s = line.split()
            cinact = float(s[0])
            cdry = float(s[1])'''

            f_cnf.close()
        finally:
            self.nlay = cnf_nlay
            self.nrow = cnf_nrow
            self.ncol = cnf_ncol

            self.delr = Util2d(model, (self.ncol,), np.float32, cnf_delr,
                                name='delr', locat=self.unit_number[0])
            self.delc = Util2d(model, (self.nrow,), np.float32, cnf_delc,
                                name='delc', locat=self.unit_number[0])
            self.top = Util2d(model, (self.nrow, self.ncol), np.float32,
                               cnf_top, name='model_top',
                               locat=self.unit_number[0])

            cnf_botm = np.empty((self.nlay + sum(self.laycbd), self.nrow,
                                 self.ncol))

            # First model layer
            cnf_botm[0:, :, :] = cnf_top - cnf_dz[0, :, :]
            # All other layers
            for l in range(1, self.nlay):
                cnf_botm[l, :, :] = cnf_botm[l - 1, :, :] - cnf_dz[l, :, :]

            self.botm = Util3d(model, (self.nlay + sum(self.laycbd),
                                        self.nrow, self.ncol), np.float32,
                                cnf_botm, 'botm',
                                locat=self.unit_number[0])

    def gettop(self):
        """
        Get the top array.

        Returns
        -------
        top : array of floats (nrow, ncol)
        """
        return self.top.array

    def getbotm(self, k=None):
        """
        Get the bottom array.

        Returns
        -------
        botm : array of floats (nlay, nrow, ncol), or

        botm : array of floats (nrow, ncol) if k is not none
        """
        if k is None:
            return self.botm.array
        else:
            return self.botm.array[k, :, :]

    def __calculate_thickness(self):
        thk = []
        thk.append(self.top - self.botm[0])
        for k in range(1, self.nlay + sum(self.laycbd)):
            thk.append(self.botm[k - 1] - self.botm[k])
        self.__thickness = Util3d(self.parent, (self.nlay + sum(self.laycbd),
                                                 self.nrow, self.ncol),
                                   np.float32, thk, name='thickness')

    @property
    def thickness(self):
        """
        Get a Util3d array of cell thicknesses.

        Returns
        -------
        thickness : util3d array of floats (nlay, nrow, ncol)

        """
        return self.__thickness

    def write_file(self):
        """
        Write the package file.

        Returns
        -------
        None

        """
        # Open file for writing
        f_dis = open(self.fn_path, 'w')
        # Item 0: heading        
        f_dis.write('{0:s}\n'.format(self.heading))
        f_dis.write('#{0:s}'.format(str(self.sr)))
        f_dis.write(",{0:s}\n".format(self.start_datetime))
        # Item 1: NLAY, NROW, NCOL, NPER, ITMUNI, LENUNI
        f_dis.write('{0:10d}{1:10d}{2:10d}{3:10d}{4:10d}{5:10d}\n' \
                    .format(self.nlay, self.nrow, self.ncol, self.nper,
                            self.itmuni, self.lenuni))
        # Item 2: LAYCBD
        for l in range(0, self.nlay):
            f_dis.write('{0:3d}'.format(self.laycbd[l]))
        f_dis.write('\n')
        # Item 3: DELR
        f_dis.write(self.delr.get_file_entry())
        # Item 4: DELC       
        f_dis.write(self.delc.get_file_entry())
        # Item 5: Top(NCOL, NROW)
        f_dis.write(self.top.get_file_entry())
        # Item 5: BOTM(NCOL, NROW)        
        f_dis.write(self.botm.get_file_entry())

        # Item 6: NPER, NSTP, TSMULT, Ss/tr
        for t in range(self.nper):
            f_dis.write('{0:14f}{1:14d}{2:10f} '.format(self.perlen[t],
                                                        self.nstp[t],
                                                        self.tsmult[t]))
            if self.steady[t]:
                f_dis.write(' {0:3s}\n'.format('SS'))
            else:
                f_dis.write(' {0:3s}\n'.format('TR'))
        f_dis.close()

    def check(self, f=None, verbose=True, level=1):
        """
        Check dis package data for zero and negative thicknesses.

        Parameters
        ----------
        f : str or file handle
            String defining file name or file handle for summary file
            of check method output. If a sting is passed a file handle
            is created. If f is None, check method does not write
            results to a summary file. (default is None)
        verbose : bool
            Boolean flag used to determine if check method results are
            written to the screen
        level : int
            Check method analysis level. If level=0, summary checks are
            performed. If level=1, full checks are performed.

        Returns
        -------
        None

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow.load('model.nam')
        >>> m.dis.check()
        """
        if f is not None:
            if isinstance(f, str):
                pth = os.path.join(self.parent.model_ws, f)
                f = open(pth, 'w', 0)

        errors = False
        txt = '\n{} PACKAGE DATA VALIDATION:\n'.format(self.name[0])
        t = ''
        t1 = ''
        inactive = self.parent.bas6.ibound.array == 0
        # thickness errors
        d = self.thickness.array
        d[inactive] = 1.
        if d.min() <= 0:
            errors = True
            t = '{}  ERROR: Negative or zero cell thickness specified.\n'.format(t)
            if level > 0:
                idx = np.column_stack(np.where(d <= 0.))
                t1 = self.level1_arraylist(idx, d, self.thickness.name, t1)
        else:
            t = '{}  Specified cell thickness is OK.\n'.format(t)

        # add header to level 0 text
        txt += t

        if level > 0:
            if errors:
                txt += '\n  DETAILED SUMMARY OF {} ERRORS:\n'.format(self.name[0])
                # add level 1 header to level 1 text
                txt += t1

        # write errors to summary file
        if f is not None:
            f.write('{}\n'.format(txt))

        # write errors to stdout
        if verbose:
            print(txt)

    @staticmethod
    def load(f, model, ext_unit_dict=None):
        """
        Load an existing package.

        Parameters
        ----------
        f : filename or file handle
            File to load.
        model : model object
            The model object (of type :class:`flopy.modflow.mf.Modflow`) to
            which this package will be added.
        ext_unit_dict : dictionary, optional
            If the arrays in the file are specified using EXTERNAL,
            or older style array control records, then `f` should be a file
            handle.  In this case ext_unit_dict is required, which can be
            constructed using the function
            :class:`flopy.utils.mfreadnam.parsenamefile`.

        Returns
        -------
        dis : ModflowDis object
            ModflowDis object.

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow()
        >>> dis = flopy.modflow.ModflowDis.load('test.dis', m)

        """

        if model.verbose:
            sys.stdout.write('loading dis package file...\n')

        if not hasattr(f, 'read'):
            filename = f
            f = open(filename, 'r')
        # dataset 0 -- header
        header = ''
        while True:
            line = f.readline()
            if line[0] != '#':
                break
            header += line.strip()


        header = header.replace('#','')
        xul, yul = None, None
        rotation = 0.0
        proj4_str = "EPSG:4326"
        start_datetime = "1/1/1970"

        for item in header.split(','):
            item = item.lower()
            if "xul" in item:
                try:
                    xul = float(item.split(':')[1])
                except:
                    pass
            elif "yul" in item:
                try:
                    yul = float(item.split(':')[1])
                except:
                    pass
            elif "rotation" in item:
                try:
                    rotation = float(item.split(':')[1])
                except:
                    pass
            elif "proj4_str" in item:
                try:
                    proj4_str = ':'.join(item.split(':')[1:])
                except:
                    pass
            elif "start" in item:
                try:
                    start_datetime = item.split(':')[1]
                except:
                    pass

        # dataset 1
        nlay, nrow, ncol, nper, itmuni, lenuni = line.strip().split()[0:6]
        nlay = int(nlay)
        nrow = int(nrow)
        ncol = int(ncol)
        nper = int(nper)
        itmuni = int(itmuni)
        lenuni = int(lenuni)
        # dataset 2 -- laycbd
        if model.verbose:
            print('   Loading dis package with:\n      ' + \
                  '{0} layers, {1} rows, {2} columns, and {3} stress periods'.format(nlay, nrow, ncol, nper))
            print('   loading laycbd...')
        laycbd = np.empty((nlay), dtype=np.int)
        d = 0
        while True:
            line = f.readline()
            raw = line.strip('\n').split()
            for val in raw:
                laycbd[d] = np.int(val)
                d += 1
                if d == nlay:
                    break
            if d == nlay:
                break
        # dataset 3 -- delr
        if model.verbose:
            print('   loading delr...')
        delr = Util2d.load(f, model, (1, ncol), np.float32, 'delr',
                            ext_unit_dict)
        delr = delr.array.reshape((ncol))
        #dataset 4 -- delc
        if model.verbose:
            print('   loading delc...')
        delc = Util2d.load(f, model, (1, nrow), np.float32, 'delc',
                            ext_unit_dict)
        delc = delc.array.reshape((nrow))
        #dataset 5 -- top
        if model.verbose:
            print('   loading top...')
        top = Util2d.load(f, model, (nrow, ncol), np.float32, 'top',
                           ext_unit_dict)
        #dataset 6 -- botm
        if model.verbose:
            print('   loading botm...')
        ncbd = laycbd.sum()
        if nlay > 1:
            botm = Util3d.load(f, model, (nlay + ncbd, nrow, ncol), np.float32,
                                'botm', ext_unit_dict)
        else:
            botm = Util3d.load(f, model, (nlay, nrow, ncol), np.float32, 'botm',
                                ext_unit_dict)
        #dataset 7 -- stress period info
        if model.verbose:
            print('   loading stress period data...')
        perlen = []
        nstp = []
        tsmult = []
        steady = []
        for k in range(nper):
            line = f.readline()
            a1, a2, a3, a4 = line.strip().split()[0:4]
            a1 = float(a1)
            a2 = int(a2)
            a3 = float(a3)
            if a4.upper() == 'TR':
                a4 = False
            else:
                a4 = True
            perlen.append(a1)
            nstp.append(a2)
            tsmult.append(a3)
            steady.append(a4)

        # create dis object instance
        dis = ModflowDis(model, nlay, nrow, ncol, nper, delr, delc, laycbd,
                         top, botm, perlen, nstp, tsmult, steady, itmuni,
                         lenuni, xul=xul, yul=yul, rotation=rotation,
                         proj4_str=proj4_str, start_datetime=start_datetime)
        # return dis object instance
        return dis





