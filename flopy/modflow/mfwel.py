"""
mfwel module.  Contains the ModflowWel class. Note that the user can access
the ModflowWel class as `flopy.modflow.ModflowWel`.

Additional information for this MODFLOW package can be found at the `Online
MODFLOW Guide
<http://water.usgs.gov/ogw/modflow/MODFLOW-2005-Guide/index.html?wel.htm>`_.

"""

import numpy as np
from flopy.mbase import Package
from flopy.utils.util_list import mflist
from mfparbc import ModflowParBc as mfparbc

class ModflowWel(Package):
    """
    MODFLOW Well Package Class.

    Parameters
    ----------
    model : model object
        The model object (of type :class:`flopy.modflow.mf.Modflow`) to which
        this package will be added.
    iwelcb : int
        is a flag and a unit number. (the default is 0).
    layer_row_column_data : list of records
        In its most general form, this is a triple list of well records  The
        innermost list is the layer, row, column, and flux rate for a single
        well.  Then for a stress period, there can be a list of wells.  Then
        for a simulation, there can be a separate list for each stress period.
        This gives the form of
            lrcq = [
                     [  #stress period 1
                       [l1, r1, c1, q1],
                       [l2, r2, c2, q2],
                       [l3, r3, c3, q3],
                       ],
                     [  #stress period 2
                       [l1, r1, c1, q1],
                       [l2, r2, c2, q2],
                       [l3, r3, c3, q3],
                       ], ...
                     [  #stress period kper
                       [l1, r1, c1, q1],
                       [l2, r2, c2, q2],
                       [l3, r3, c3, q3],
                       ],
                    ]
        Note that if there are not records in layer_row_column_data, then the
        last group of wells will apply until the end of the simulation.
    layer_row_column_Q : list of records
        Deprecated - use layer_row_column_data instead.
    options : list of strings
        Package options. (default is None).
    naux : int
        number of auxiliary variables
    extension : string
        Filename extension (default is 'wel')
    unitnumber : int
        File unit number (default is 11).
    zerobase : boolean (default is True)
        True when zero-based indices are used: layers, rows, columns start at 0
        False when one-based indices are used: layers, rows, columns start at 1 (deprecated)


    Attributes
    ----------
    mxactw : int
        Maximum number of wells for a stress period.  This is calculated
        automatically by FloPy based on the information in
        layer_row_column_data.

    Methods
    -------

    See Also
    --------

    Notes
    -----
    Parameters are not supported in FloPy.

    Examples
    --------

    >>> import flopy
    >>> m = flopy.modflow.Modflow()
    >>> lrcq = [[[2, 3, 4, -100.]]]  #this well will be applied to all stress
    >>>                              #periods
    >>> wel = flopy.modflow.ModflowWel(m, layer_row_column_data=lrcq)

    """
    def __init__(self, model, ipakcb=0, stress_period_data=None,dtype=None,
                 extension ='wel', unitnumber=20, options=None,
                 specify=False, phiramp=0.05, phiramp_unit=2):
        """
        Package constructor.

        """
        # Call parent init to set self.parent, extension, name and unit number
        Package.__init__(self, model, extension, 'WEL', unitnumber)
        self.heading = '# Well file for MODFLOW, generated by Flopy.'
        self.url = 'wel.htm'
        self.ipakcb = ipakcb # no cell by cell terms are written
        self.specify = specify
        self.phiramp = phiramp
        self.phiramp_unit = phiramp_unit
        self.np = 0
        if options is None:
            options = []
        self.options = options
        self.parent.add_package(self)
        if dtype is not None:
            self.dtype = dtype
        else:
            self.dtype = self.get_default_dtype()
        self.stress_period_data = mflist(model,self.dtype,stress_period_data)

    def __repr__( self ):
        return 'Well package class'

    def ncells( self):
        # Returns the  maximum number of cells that have a well
        # (developed for MT3DMS SSM package)
        return self.stress_period_data.mxact

    def write_file(self):
        """
        Write the file.

        """
        f_wel = open(self.fn_path, 'w')
        f_wel.write('%s\n' % self.heading)
        line = (' {0:9d} {1:9d}'.format(self.stress_period_data.mxact, self.ipakcb))
        
        if self.specify and self.parent.version is 'mfnwt':
          f_wel.write('SPECIFY {0:10.5g} {1:10d}\n'.format(self.phiramp, self.phiramp_unit))
        
        for opt in self.options:
            line += ' ' + str(opt)
        line += '\n'
        f_wel.write(line)
        self.stress_period_data.write_transient(f_wel)
        f_wel.close()

    def add_record(self,kper,index,values):
        try:
            self.stress_period_data.add_record(kper,index,values)
        except Exception as e:
            raise Exception("mfwel error adding record to list: "+str(e))

    @staticmethod
    def get_default_dtype():
        dtype = np.dtype([("k",np.int),("i",np.int),\
                         ("j",np.int),("flux",np.float32)])
        return dtype


    @staticmethod
    def get_empty(ncells=0,aux_names=None):
        #get an empty recaray that correponds to dtype
        dtype = ModflowWel.get_default_dtype()
        if aux_names is not None:
            dtype = Package.add_to_dtype(dtype,aux_names,np.float32)
        d = np.zeros((ncells,len(dtype)),dtype=dtype)

        d[:,:] = -1.0E+10
        return np.core.records.fromarrays(d.transpose(),dtype=dtype)

    @staticmethod
    def load(f, model, nper=None, ext_unit_dict=None):
        """
        Load an existing package.

        Parameters
        ----------
        f : filename or file handle
            File to load.
        model : model object
            The model object (of type :class:`flopy.modflow.mf.Modflow`) to
            which this package will be added.
        nper : int
            The number of stress periods.  If nper is None, then nper will be
            obtained from the model object. (default is None).
        ext_unit_dict : dictionary, optional
            If the arrays in the file are specified using EXTERNAL,
            or older style array control records, then `f` should be a file
            handle.  In this case ext_unit_dict is required, which can be
            constructed using the function
            :class:`flopy.utils.mfreadnam.parsenamefile`.

        Returns
        -------
        wel : ModflowWel object
            ModflowWel object.

        Examples
        --------

        >>> import flopy
        >>> m = flopy.modflow.Modflow()
        >>> wel = flopy.modflow.mfwel.load('test.wel', m)

        """
        dtype = np.dtype([("layer", np.int), ("row", np.int),
                          ("column", np.int), ("flux", np.float32)])
        if type(f) is not file:
            filename = f
            f = open(filename, 'r')
        #dataset 0 -- header
        while True:
            line = f.readline()
            if line[0] != '#':
                break
        #--check for parameters
        if "parameter" in line.lower():
            t = line.strip().split()
            #assert int(t[1]) == 0,"Parameters are not supported"
            npwel = np.int(t[1])
            mxl = 0
            if npwel > 0:
                mxl = np.int(t[2])
            line = f.readline()
        #dataset 2a
        t = line.strip().split()
        #mxactw, iwelcb = t[0:3]
        mxactw = int(t[0])
        iwelcb = 0
        try:
            if int(t[1]) != 0:
                iwelcb = 53
        except:
            pass

        options = []
        naux = 0
        if len(t) > 2:
            for toption in t[3:-1]:
                if toption.lower() is 'noprint':
                    options.append(toption)
                elif 'aux' in toption.lower():
                    naux += 1
                    options.append(toption)
        
        #--
        readNext = False
        specify = False
        line = f.readline()
        #--test for specify keyword if a NWT well file - This is a temporary hack
        if 'specify' in line.lower():
            readNext = False
            specify = True
            line = f.readline() #ditch line -- possibly save for NWT output
            t = line.strip().split()
            phiramp = np.float32(t[1])
            try:
                phiramp_unit = np.int32(t[2])
            except:
                phiramp_unit = 2
        
        #--number of columns to read
        nitems = 4 + naux

        #--read parameter data
        if npwel > 0:
            well_parms = mfparbc.load(f, npwel)
        
        if nper is None:
            nrow, ncol, nlay, nper = model.get_nrow_ncol_nlay_nper()
            
        #read data for every stress period
        stress_period_data = {}
        current = []
        for iper in xrange(nper):
            print "   loading wells for kper {0:5d}".format(iper+1)
            line = f.readline()
            #--test for specify keyword if a NWT well file - This is a temporary hack
            if 'specify' in line.lower():
                specify = True
                line = f.readline() #ditch line -- possibly save for NWT output
                t = line.strip().split()
                phiramp = np.float32(t[1])
                try:
                    phiramp_unit = np.int32(t[2])
                except:
                    phiramp_unit = 2
            t = line.strip().split()
            itmp = int(t[0])
            itmpnp = 0
            try:
                itmpnp = int(t[1])
            except:
                pass

            if itmp == 0:
                current = []
            elif itmp > 0:
                for ibnd in xrange(itmp):
                    line = f.readline()
                    t = line.strip().split()
                    bnd = []
                    for jdx in xrange(nitems):
                        if jdx < 3:
                            bnd.append(int(t[jdx])-1) #convert to zero-based.
                        else:
                            bnd.append(float(t[jdx]))
                    current.append(bnd)
            #--parameters
            for iparm in xrange(itmpnp):
                line = f.readline()
                t = line.strip().split()
                pname = t[0]
                iname = 'static'
                try:
                    tn = t[1]
                    iname = tn
                except:
                    pass
                print pname, iname
                current_dict = well_parms[pname]
                data_dict = current_dict[4][iname]
                print current_dict[0:4]
                print data_dict
                
            #layer_row_column_data.append(current)
            stress_period_data[iper] = np.array(current)
        if specify:
            wel = ModflowWel(model, iwelcb, layer_row_column_data=layer_row_column_data, 
                             options=options, naux=naux, 
                             specify=specify, phiramp=phiramp, phiramp_unit=phiramp_unit)
        else:
            wel = ModflowWel(model, iwelcb, layer_row_column_data=layer_row_column_data, 
                             options=options, naux=naux)
        return wel

