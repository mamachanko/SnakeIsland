import vigra as vg
import numpy as np
from time import time

from matplotlib import pylab as pl
from mpl_toolkits.axes_grid1 import ImageGrid

#Helper function
def msVector2ImageMagnitude(gg_array):
    return np.sqrt(np.sum(gg_array**2,-1))


def msVector2ImageAngle(gg_array):
    return np.arctan2(gg_array[...,0],gg_array[...,1])*180/np.pi


#Gaussian gradient functions
def msGaussianGradient(vol, sigma):
    shp = vol.shape
    res = np.zeros((shp[0],shp[1],shp[2], 2))
    for i in range(shp[2]):
         res[:,:,i,:] = vg.filters.gaussianGradient(vg.Image(vol[...,i]),sigma)
    return res


def msGaussianGradientMagnitude(vol, sigma):
    return msVector2ImageMagnitude(msGaussianGradient(vol, sigma))


#multispectral gradients
def msMeanGradient(gg_array):
    return np.mean(gg_array,2)


def msMaxGradient(gg_array):
    ggm_array = msVector2ImageMagnitude(gg_array)
    shp = ggm_array.shape
    x,y = np.indices((shp[0], shp[1]))
    max_g = np.argmax(ggm_array,2)
    res = gg_array[x,y,max_g,:]

    return res

def msMVGradient(gg_array):
    shp = gg_array.shape
    x2_y2_sums = np.sum(gg_array*gg_array,-2)

    a11 = x2_y2_sums[...,0]
    a12 = np.sum(gg_array[...,0]*gg_array[...,1],-1)
    a22 = x2_y2_sums[...,1]

    #Drewniok
    lambda_max = 0.5*(a11+a22 + np.sqrt( (a11 - a22)**2 + 4*a12**2))
    lambda_min = 0.5*(a11+a22 - np.sqrt( (a11 - a22)**2 + 4*a12**2))
    phi_max = np.arctan2(lambda_max - a11, a12)

    #Hamester (slower, because two trigonometrics are needed,compared to one sqrt above)
    #phi_max = 0.5*np.arctan2((2*a12),(a11 - a22))      
    #lambda_max = a11*np.cos(phi_max)**2 + 2*a12*np.sin(phi_max)*np.cos(phi_max) + a22*np.sin(phi_max)**2
    lambda_max =np.sqrt(lambda_max/shp[2])
    lambda_min =np.sqrt(lambda_min/shp[2])

    res =  np.zeros((shp[0],shp[1],2))
    res[...,0] = np.cos(phi_max)*lambda_max
    res[...,1] = np.sin(phi_max)*lambda_max


    voting =  np.zeros((shp[0],shp[1]))
    for ch in range(shp[2]):
        voting += np.sign(np.sum(res[...,:] * gg_array[...,ch,:],-1))

    voting = np.sign(voting)

    res[...,0] *= voting
    res[...,1] *= voting

    return res, lambda_max, lambda_min


def plotEdgelList(el, plot_area = None):
    arr = np.array(el)
    if plot_area == None:
        pl.plot(arr[:,0],arr[:,1], ".",markersize=1.4)
    else:
        plot_area.plot(arr[:,0],arr[:,1], ".",markersize=1.4)

def msCompareResults(vol, sigma, shrink_factor=0.5, gui=True, edge_quantil=0.05):
    start = time()
    grad =  msGaussianGradient(vol, sigma)
    elapsed = time() - start
    print "msGaussianGradient took %f seconds to finish" % elapsed

    shp = vol.shape
    weight = np.array(range(shp[2]))
    for ch in range(shp[2]/2):
        grad[...,ch,:] *= weight[ch]

    start = time()
    mean_g = msMeanGradient(grad)   
    elapsed = time() - start
    print "msMeanGradient took %f seconds to finish" % elapsed
    stddev_g = msVector2ImageMagnitude(np.std(grad,2))

    start = time()
    max_g = msMaxGradient(grad)    
    elapsed = time() - start
    print "msMaxGradient took %f seconds to finish" % elapsed

    start = time()
    mv_g , semi_major_g, semi_minor_g = msMVGradient(grad)    
    elapsed = time() - start
    print "msMVGradient took %f seconds to finish" % elapsed
        
    eccentricity_g = np.sqrt(1-semi_minor_g**2/semi_major_g**2)
    
    mean_el = np.array(vg.analysis.cannyEdgelList(vg.Vector2Image(mean_g),np.max(msVector2ImageMagnitude(mean_g))*edge_quantil))
    max_el = np.array(vg.analysis.cannyEdgelList(vg.Vector2Image(max_g),  np.max(msVector2ImageMagnitude(max_g))*edge_quantil))
    mv_el = np.array(vg.analysis.cannyEdgelList(vg.Vector2Image(mv_g),    np.max(msVector2ImageMagnitude(mv_g))*edge_quantil))
    
    if (gui):
        F_mag = pl.figure()
        F_mag.clf()     
        pl.jet()
        grid_mag = ImageGrid(F_mag, 111, \
                      nrows_ncols = (1, 3),\
                      direction="row",\
                      axes_pad = 0.05,\
                      add_all=True,\
                      label_mode = "1",\
                      share_all = True,\
                      cbar_location="right",\
                      cbar_mode="single",\
                      cbar_size="10%",\
                      cbar_pad=0.05)

        max_v = np.max(msVector2ImageMagnitude(mv_g))
        min_v = np.min(msVector2ImageMagnitude(mv_g))
    
        import matplotlib.colors
        norm = matplotlib.colors.normalize(vmax=max_v, vmin=min_v)
        
        grid_mag[0].imshow(msVector2ImageMagnitude(mean_g),norm=norm)
        pl.title("Mean Gradient Mag.")
    
        #pl.figure()
        #pl.subplot(132)
        grid_mag[1].imshow(msVector2ImageMagnitude(max_g), norm=norm)
        pl.title("Max Gradient Mag.")
    
        #pl.figure()
        #pl.subplot(133)
        img_mag = grid_mag[2].imshow(msVector2ImageMagnitude(mv_g), norm=norm)
        pl.title("MV Gradient Mag.")
        grid_mag[2].cax.colorbar(img_mag)
        
	print 'check'        
        F_ang = pl.figure()
        F_ang.clf()     
        pl.hsv()
        grid_ang = ImageGrid(F_ang, 111, \
                      nrows_ncols = (1, 3),\
                      direction="row",\
                      axes_pad = 0.05,\
                      add_all=True,\
                      label_mode = "1",\
                      share_all = True,\
                      cbar_location="right",\
                      cbar_mode="single",\
                      cbar_size="10%",\
                      cbar_pad=0.05)
            
        norm = matplotlib.colors.normalize(vmax=180, vmin=-180)
        grid_ang[0].imshow(msVector2ImageAngle(mean_g), norm=norm)
        pl.title("Mean Gradient Angle")
    
        grid_ang[1].imshow(msVector2ImageAngle(max_g), norm=norm)
        pl.title("Max Gradient Angle")
    
        img_ang = grid_ang[2].imshow(msVector2ImageAngle(mv_g), norm=norm)
        pl.title("MV Gradient Angle")
        grid_ang[2].cax.colorbar(img_ang)
        
        
        
        F_edg = pl.figure()
        F_edg.clf()     
        pl.hsv()
        grid_edg = ImageGrid(F_edg, 111, \
                      nrows_ncols = (1, 3),\
                      direction="row",\
                      axes_pad = 0.05,\
                      add_all=True,\
                      label_mode = "1",\
                      share_all = True,\
                      cbar_location="right",\
                      cbar_mode="single",\
                      cbar_size="10%",\
                      cbar_pad=0.05)
        
        
        grid_edg[0].axis([0, shp[0]-1, shp[1]-1, 0])
        grid_edg[1].axis([0, shp[0]-1, shp[1]-1, 0])
        grid_edg[2].axis([0, shp[0]-1, shp[1]-1, 0])
        plotEdgelList(mean_el, grid_edg[0])
        plotEdgelList(max_el,  grid_edg[1])
        plotEdgelList(mv_el,   grid_edg[2])
        
        #pl.figure()
        #pl.subplot(131,aspect="equal")
        #pl.axis([0, shp[0]-1, shp[1]-1, 0])
        #plotEdgelList(mean_el)
        #pl.title("Mean Gradient Edgel")

        #pl.subplot(132,aspect="equal")
        #pl.axis([0, shp[0]-1, shp[1]-1, 0])
        #plotEdgelList(max_el)
        #pl.title("Max Gradient Edgel")

        #pl.subplot(133,aspect="equal")
        #pl.axis([0, shp[0]-1, shp[1]-1, 0])
        #plotEdgelList(mv_el)
        #pl.title("MV Gradient Edgel")
    
    
        ## MV semi-major and semi-minor axis
        pl.figure()
        pl.subplot(121)
        pl.imshow(semi_major_g)
        pl.copper()
        pl.colorbar(shrink=shrink_factor)
        pl.title("Gradient MV semi-major axis")
    
        pl.subplot(122)
        pl.imshow(semi_minor_g)
        pl.colorbar(shrink=shrink_factor)
        pl.title("Gradient MV semi-minor axis")
        
        
        ## Std. dev of MS Gradients vs. Eccentricity of the MV eigenvals
        pl.figure()
        pl.subplot(121)
        pl.imshow(stddev_g)
        pl.copper()
        pl.colorbar(shrink=shrink_factor)
        pl.title("Gradient std. dev.")
    
        pl.subplot(122)
        pl.imshow(eccentricity_g)
        pl.colorbar(shrink=shrink_factor)
        pl.title("Gradient MV eccentricity")

	pl.show()
