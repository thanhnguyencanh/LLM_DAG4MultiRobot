import pybullet as p

# Input mesh file
input_obj = "textured.obj"
output_obj = "textured_vhacd.obj"

p.vhacd(input_obj, output_obj, "path/to/log.txt",
        concavity=0.0025,
        alpha=0.04,
        beta=0.05,
        resolution=100000,
        depth=20,
        planeDownsampling=4,
        convexhullDownsampling=4,
        pca=0,
        mode=0,
        convexhullApproximation=1)