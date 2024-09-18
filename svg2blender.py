#!/usr/bin/env python3
import os, sys, io, zipfile, xml.dom.minidom, subprocess, math, json
from random import random, uniform

try:
	import bpy, mathutils
except:
	bpy = None

SCRIPTS = []
GameSim = {'eyes':[], 'heads':[], 'bots':[]}

def parse_svg(src, gscripts, x=0, y=0, kra_fname=''):
	svg = xml.dom.minidom.parseString(open(src).read())
	print(svg.toxml())
	svg_width = svg.getElementsByTagName('svg')[0].getAttribute('width')
	svg_height = svg.getElementsByTagName('svg')[0].getAttribute('height')
	if svg_width.endswith( ('px','mm') ): svg_width = svg_width[:-2]
	if svg_height.endswith( ('px','mm') ): svg_height = svg_height[:-2]
	if svg_width.strip():
		svg_width = float(svg_width)
		svg_height = float(svg_height)
	else:
		svg_width = svg_height = 512

	for g in svg.getElementsByTagName('g'):
		for c in g.childNodes:
			if hasattr(c, 'tagName') and c.tagName=='desc':
				gscripts[g.getAttribute('id')] = c.firstChild.nodeValue
				break

	bobs = []
	rects = []
	#for elt in svg.getElementsByTagName('rect'):
	eidx = 0
	for elt in svg.documentElement.childNodes:
		if not hasattr(elt, 'tagName'): continue
		if elt.tagName in 'metadata defs sodipodi:namedview'.split():
			continue
		if elt.tagName=='rect':
			r = {
				'x' : float(elt.getAttribute('x')),
				'y' : float(elt.getAttribute('y')),
				'width' : float(elt.getAttribute('width')),
				'height' : float(elt.getAttribute('height')),
				'color'  : elt.getAttribute('fill'),
				'round'  : elt.getAttribute('ry'),
				'index'  : eidx,
			}
			if not r['color'].strip():
				css = elt.getAttribute('style')
				if 'fill:' in css:
					r['color'] = css.split('fill:')[-1].split(';')[0]
			rects.append(r)
		if elt.tagName=='g':
			## check one level deep
			for e in elt.childNodes:
				if hasattr(e,'tagName'):
					if e.tagName=='rect':
						r = {
							'x' : float(e.getAttribute('x')),
							'y' : float(e.getAttribute('y')),
							'width' : float(e.getAttribute('width')),
							'height' : float(e.getAttribute('height')),
							'color'  : e.getAttribute('fill'),
							'round'  : e.getAttribute('ry'),
							'index'  : eidx,
						}
						if not r['color'].strip():
							css = e.getAttribute('style')
							if 'fill:' in css:
								r['color'] = css.split('fill:')[-1].split(';')[0]

						rects.append(r)

					eidx += 1
		else:
			eidx += 1

	texts = svg.getElementsByTagName('text')
	if texts:
		for t in texts:
			if not len(t.childNodes): continue
			print(t.toxml())
			clr = None
			if t.hasAttribute('style'):
				style = t.getAttribute('style')
				fontsize = style.split('font-size:')[-1].split(';')[0]
				assert fontsize.endswith('px')
				fontsize = float(fontsize[:-2])
				print('fontsize:', fontsize)
				if 'fill:' in style:
					clr = style.split('fill:')[-1].split(';')[0]
					print('color:', clr)



			tid = t.getAttribute('id')
			if t.hasAttribute('x'):
				tx  = float(t.getAttribute('x'))
				ty  = float(t.getAttribute('y'))
			else:
				tx = ty = 0
			tscl = t.getAttribute('transform')
			if tscl.startswith('scale('):
				tsx, tsy = tscl.split('(')[-1].split(')')[0].split(',')
				tsx = float(tsx)
				tsy = float(tsy)
			else:
				tsx = tsy = 1.0

			if tscl.startswith('rotate('):
				trot = float( tscl.split('(')[-1].split(')')[0] )
				print('rotate:', trot)
			else:
				trot = 0


			inkscript = []
			for child in t.childNodes:
				if child.tagName=='desc':
					## INKSCAPE metadata
					inkscript.append(child.firstChild.nodeValue)
					break
			for child in t.getElementsByTagName('tspan'):
				style = child.getAttribute('style')
				if style:
					fontsize = style.split('font-size:')[-1].split(';')[0]
					assert fontsize.endswith('px')
					fontsize = float(fontsize[:-2])

				text = child.firstChild.nodeValue
				if not text:
					if child.hasAttribute('x'):
						tx  = float(child.getAttribute('x'))
						ty  = float(child.getAttribute('y'))

				if bpy and text:
					bpy.ops.object.text_add()
					ob = bpy.context.active_object
					ob.data.body = text
					ob.name = tid
					ob.rotation_euler.x = math.pi/2
					ob.data.size=fontsize * 0.025
					ob.data.extrude = ob.data.size * 0.5
					ob.scale.x = tsx
					ob.scale.y = tsy
					ob.location.x = tx * 0.01
					ob.location.z = ty * 0.01
					#ob.location.x -= 1  ## TODO calc offset from svg
					#ob.location.z -= 0.5
					if trot:
						ob.rotation_euler.y = math.radians(trot)
					if clr:
						if clr and clr.startswith('#'):
							if clr in bpy.data.materials:
								mat = bpy.data.materials[clr]
							else:
								mat = bpy.data.materials.new(name=clr)
								r,g,b = hex2rgb(clr[1:])
								mat.diffuse_color[0] = r / 255
								mat.diffuse_color[1] = g / 255
								mat.diffuse_color[2] = b / 255

							ob.data.materials.append(mat)

					bobs.append(ob)
					if inkscript:
						sco = {'bpy':bpy, 'self':ob, 'math':math, 'random':random}
						sco[tid] = ob
						txt = bpy.data.texts.new(name=tid+'.'+kra_fname)
						txt.from_string('\n'.join(inkscript))
						SCRIPTS.append({'scope':sco, 'script':txt})
	if bpy:
		groups = []
		gstep = 0.01
		#for g in svg.getElementsByTagName('g'):
		for g in []:
			is_leaf = True
			for c in g.childNodes:
				if hasattr(c,'tagName') and c.tagName=='g':
					is_leaf=False
					break
			if not is_leaf:
				continue
			groups.append(g)
			xdefs = ''
			if len(svg.getElementsByTagName('defs')):
				xdefs = svg.getElementsByTagName('defs')[0].toxml()

			gsvg = [
				'<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
				'<svg width="%s" height="%s" viewBox="%s" version="1.1">' % (
					svg.documentElement.getAttribute('width'),
					svg.documentElement.getAttribute('height'),
					svg.documentElement.getAttribute('viewBox'),
				),
				xdefs,
				g.toxml(),
				'</svg>',
			]
			open('/tmp/%s.svg' %g.getAttribute('id'), 'w').write('\n'.join(gsvg))
			#bpy.ops.wm.gpencil_import_svg(filepath=src, scale=100, resolution=5)
			bpy.ops.wm.gpencil_import_svg(filepath='/tmp/%s.svg' %g.getAttribute('id'), scale=50, resolution=5)
			ob = bpy.context.active_object
			#ob.name = layer.getAttribute('name')
			ob.name = g.getAttribute('id')
			bobs.append(ob)
			ob.location.x = x * 0.01
			ob.location.z = -y * 0.01

			ob.location.y = -len(groups) * gstep
			depth_faker( ob )

			if ob.name in gscripts:
				sco = {'bpy':bpy, 'self':ob, 'math':math, 'random':random}
				sco[ob.name] = ob
				txt = bpy.data.texts.new(name=ob.name+'.'+kra_fname)
				txt.from_string(gscripts[ob.name])
				SCRIPTS.append({'scope':sco, 'script':txt})
		if not groups:
			bpy.ops.wm.gpencil_import_svg(filepath=src, scale=50, resolution=5)  ## TODO recenter_bounds=False
			ob = bpy.context.active_object
			#ob.name = layer.getAttribute('name')
			bobs.append(ob)
			ob.location.x = x * 0.01
			ob.location.z = -y * 0.01
			print('num layers:', len(ob.data.layers))
			if len(ob.data.layers) > 100:
				depth_faker( ob, lstep=0.001, sstep=0.001 )
			elif len(ob.data.layers) > 50:
				depth_faker( ob, lstep=0.003, sstep=0.003 )
			else:
				depth_faker( ob )
			gpsvg = ob
			gpsvg.hide_select=True
			if len(gpsvg.data.layers)==1:
				assert len(gpsvg.data.layers[0].frames)==1
				gpstrokes = gpsvg.data.layers[0].frames[0].strokes
			else:
				## if inkscape saves a flat svg no layers
				gpstrokes = None

		print('num rects:', len(rects))

		#if not gpstrokes and rects and len(rects) <= len(gpsvg.data.layers):
		if not gpstrokes and rects:
			cube_layers = {}
			for r in rects:
				print('stroke index:', r['index'])
				if r['index'] >= len(gpsvg.data.layers):
					print('ERROR: invalid layer indices')
					break
				glayer = gpsvg.data.layers[r['index']]
				stroke = glayer.frames[0].strokes[0]
				ax,ay,az = calc_avg_points( stroke )
				bpy.ops.mesh.primitive_plane_add(location=(ax,ay,az))
				ob = bpy.context.active_object
				ob.name = glayer.info
				ob.lock_location[0]=True  ## this is saved in the json, but its locked here because it is advanced use
				ob.lock_location[2]=True
				ob.lock_rotation[0]=True
				ob.lock_rotation[1]=True
				ob.lock_scale = [True,True,True]

				#ob.scale.x = (r['width']/2) * 0.01
				#ob.scale.y = (r['height']/2) * 0.01
				_w, _h = calc_width_height(stroke.points)
				ob.scale.x = _w/2
				ob.scale.y = _h/2
				ob.rotation_euler.x = math.pi/2
				ob.location.y += 0.05
				bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
				glayer.parent = ob

				cube_layers[ r['index'] ] = {'cube':ob, 'layer':glayer}

				if r['round']:
					rad = float(r['round'])
					#mod = ob.modifiers.new(name='round', type='SUBSURF')
					mod = ob.modifiers.new(name='round', type='BEVEL')
					mod.affect = 'VERTICES'
					mod.width = rad * 0.01
					mod.segments = 2

				mod = ob.modifiers.new(name='__DEPTH__',type="SOLIDIFY")
				mod.thickness = r['width'] * 0.02
				ob['__DEPTH__'] = mod.thickness

				clr = r['color']
				if clr and clr.startswith('#'):
					if clr in bpy.data.materials:
						mat = bpy.data.materials[clr]
					else:
						mat = bpy.data.materials.new(name=clr)
						r,g,b = hex2rgb(clr[1:])
						mat.diffuse_color[0] = r / 255
						mat.diffuse_color[1] = g / 255
						mat.diffuse_color[2] = b / 255

					ob.data.materials.append(mat)

			if len(gpsvg.data.layers) < 100:
				make_cube_grease_rig( gpsvg, cube_layers )

			## restore offsets
			for jfile in JSONS:
				print('restore offsets:', jfile)
				d = json.loads(open(jfile).read())
				print(d)
				for cu in bpy.data.objects:
					if cu.name in d:
						dd = d[cu.name]
						if 'x' in dd: cu.location.x = dd['x']
						if 'y' in dd: cu.location.y = dd['y']
						if 'rz' in dd: cu.rotation_euler.z = dd['rz']
						if 'depth' in dd:
							cu.modifiers['__DEPTH__'].thickness = dd['depth']


		elif rects and gpstrokes:
			bpy.ops.object.empty_add(type="ARROWS")
			root = bpy.context.active_object
			root.name='OFFSEET'

			for r in rects:
				print('stroke index:', r['index'])
				stroke = gpstrokes[r['index']]
				ax,ay,az = calc_avg_points( stroke )
				bpy.ops.mesh.primitive_plane_add(location=(ax,ay,az))
				ob = bpy.context.active_object
				#ob.scale.x = (r['width']/2) * 0.01
				#ob.scale.y = (r['height']/2) * 0.01
				_w, _h = calc_width_height(stroke.points)
				ob.scale.x = _w/2
				ob.scale.y = _h/2
				ob.rotation_euler.x = math.pi/2
				ob.location.y += 0.05

				#ob = bpy_make_rect(
				#	#r['x'] - (svg_width/2), 
				#	#r['y'] - (svg_height/2), 
				#	r['x'], 
				#	r['y'], 
				#	r['width'], 
				#	r['height']
				#)
				#ob.parent = root
				if 1:
					mod = ob.modifiers.new(name='extrude',type="SOLIDIFY")
					if az < 0:
						mod.thickness = (r['width']+r['height']) * 0.005
					else:
						mod.thickness = (r['width']+r['height']) * 0.02

				elif r['width'] > 150:  ## TODO check scale of drawing
					mod = ob.modifiers.new(name='extrude',type="SOLIDIFY")
					mod.thickness = r['width'] * 0.02
				elif abs(r['width'] - r['height']) < 10:  ## its hip to be square
					mod = ob.modifiers.new(name='extrude',type="SOLIDIFY")
					mod.thickness = r['width'] * 0.0125
				else:
					mod = ob.modifiers.new(name='extrude',type="SOLIDIFY")
					mod.thickness = r['width'] * 0.01

				clr = r['color']
				if clr and clr.startswith('#'):
					if clr in bpy.data.materials:
						mat = bpy.data.materials[clr]
					else:
						mat = bpy.data.materials.new(name=clr)
						r,g,b = hex2rgb(clr[1:])
						mat.diffuse_color[0] = r / 255
						mat.diffuse_color[1] = g / 255
						mat.diffuse_color[2] = b / 255

					ob.data.materials.append(mat)

			make_grease_layers(gpsvg)
			## TODO this is ugly
			root.location.x = -4.77 #-4.6
			root.location.z = 3.91 #3.8
			root.scale *= 1.333

	return bobs



def calc_near(object, objects):
	nob = None
	ndist = float('inf')
	v = object.location
	for ob in objects:
		dist = (v-ob.location).length
		if dist < ndist:
			nob = ob
			ndist = dist
	return nob


def calc_near_object(x,y,z, objects):
	nob = None
	ndist = float('inf')
	v = mathutils.Vector([x,y,z])
	for idx in objects:
		ob = objects[idx]['cube']
		dist = (v-ob.location).length
		if dist < ndist:
			nob = ob
			ndist = dist
	return nob


def make_cube_grease_rig( gpsvg, cube_layers ):
	def next_cube(prev_cube=None):
		nxt = None
		for i in cube_layers:
			o = cube_layers[i]['cube']
			if o.parent: continue
			if o == prev_cube: continue
			if nxt is None or o.dimensions > nxt.dimensions:
				nxt = o
		return nxt

	for idx, layer in enumerate(gpsvg.data.layers):
		if idx not in cube_layers:
			if layer.parent:
				print('layer already has parent', layer, layer.parent)
				continue
			stroke = layer.frames[0].strokes[0]
			ax,ay,az = calc_avg_points( stroke )
			p = calc_near_object(ax,ay,az, cube_layers)
			layer.parent = p

	next = next_cube()
	root_cube = next
	head_cube = None
	leg_cubes = []
	pivs = []

	bpy.ops.object.empty_add(type="CIRCLE")
	root = bpy.context.active_object
	bot  = {'root':root, 'leg_roots':pivs, 'jump':0.0}
	GameSim['bots'].append(bot)
	next.parent = root
	delta = next.location - root.location
	next.location = [0,0,0]

	lower_body = []
	head_parts = []
	while next:
		nn = next_cube(next)
		if nn:
			nn.location -= delta
			nn.parent = root_cube
			#if nn.location.z < 0:
			#	nn.parent = root_cube
			#else:
			#	nn.parent = next
			if nn.location.z > 0.1:
				if not head_cube:
					head_cube = nn
				else:
					head_parts.append(nn)
			elif len(leg_cubes) < 2 and nn.location.z < -0.1:
				if nn.dimensions.x < nn.dimensions.z / 3:
					leg_cubes.append(nn)
			if nn.location.z < -0.1:
				lower_body.append(nn)
		next = nn

	if head_cube:
		head_cube['__TYPE__']='HEAD'

	for leg in leg_cubes:
		leg['__TYPE__'] = 'LEG'
		bpy.ops.object.empty_add(type="CIRCLE", location=leg.location)
		pivot = bpy.context.active_object
		pivs.append(pivot)
		pivot.empty_display_size=0.3
		deltaz = leg.dimensions.z/2
		pivot.location.z += deltaz
		leg.parent = pivot
		leg.location = [0,0,-deltaz]

		if head_cube and abs(head_cube.location.x) > 0.75:
			mod = leg.modifiers.new(name='more-legs', type='ARRAY')
			mod.use_relative_offset = False
			mod.use_constant_offset = True
			mod.constant_offset_displace = [0,root_cube.dimensions.y*0.9,0]

	for o in lower_body:
		if o in leg_cubes: continue
		for p in pivs:
			parent = None
			if o.location.x < 0 and p.location.x < 0:
				parent = p
			elif o.location.x > 0 and p.location.x > 0:
				parent = p

			if parent:
				## https://blender.stackexchange.com/questions/152781/how-to-make-object-a-a-parentkeep-transform-of-object-b-via-blenders-python-a
				bpy.context.evaluated_depsgraph_get().update()
				# First, calculate the inverse of the parent's world matrix
				parent_inverse_world_matrix = parent.matrix_world.inverted()
				o.parent = parent
				#o.matrix_parent_inverse = o.matrix_world @ parent_inverse_world_matrix
				o.matrix_parent_inverse = parent_inverse_world_matrix
				break

	for piv in pivs:
		piv.parent = root_cube

	print('head parts:', head_parts)
	if head_cube and head_parts:
		## try to find the neck
		neck = calc_near(root_cube, head_parts)
		if not calc_overlap(head_cube, neck):
			print('looks like a neck:', neck)
			neck['__TYPE__']='NECK'
			head_parts.remove(neck)

			bpy.context.evaluated_depsgraph_get().update()
			head_cube.parent = neck
			head_cube.matrix_parent_inverse = neck.matrix_world.inverted()

			bot['neck'] = neck
		else:
			neck = None
		
		eyes = []
		ears = []
		head_parts_upper = []
		parent = head_cube
		for o in head_parts:
			print('head part:', o)
			bpy.context.evaluated_depsgraph_get().update()
			parent_inverse_world_matrix = parent.matrix_world.inverted()
			o.parent = parent
			o.matrix_parent_inverse = parent_inverse_world_matrix
			bpy.context.evaluated_depsgraph_get().update()
			if  o.location.z - parent.location.z  > 0.01:
				head_parts_upper.append(o)
			if 'eye' in o.name.lower():
				eyes.append(o)
			elif 'eye' in o.name.lower():
				ears.append(o)

		if not eyes:
			if not eyes and len(gpsvg.data.layers) <= 16:  ## only for simple drawings
				print('using fallback search for eyes')
				for idx, o in enumerate(head_parts_upper):
					if idx >= 6: break
					if o in ears: continue
					if check_object_inside_on_xz( o, head_cube ) and len(eyes) < 2:
						o['__TYPE__']='EYE'
						print('EYE', o)
						eyes.append(o)
						GameSim['eyes'].append(o)

		if not ears:
			## try to find the eyes in the first few rects
			for idx, o in enumerate(head_parts_upper):
				if idx >= 6: break
				print('head part upper:', o)
				if abs( o.dimensions.z - head_cube.dimensions.z ) < 0.2 and len(ears) < 2:
					if o.dimensions.x < o.dimensions.z:
						o['__TYPE__']='EAR'
						print('EAR',o)
						ears.append(o)
				elif abs( o.dimensions.x - head_cube.dimensions.x ) < 0.5 and len(eyes) < 2:
					o['__TYPE__']='EYE'
					print('EYE', o)
					eyes.append(o)
					GameSim['eyes'].append(o)



		if eyes or ears:
			GameSim['heads'].append(head_cube)


	for i in cube_layers:
		o = cube_layers[i]['cube']
		o['__X__'] = o.location.x
		o['__Y__'] = o.location.y
		o['__RZ__'] = o.rotation_euler.z

def check_object_inside_on_xz(obj1, obj2):
	"""Checks if object1 is inside object2 on the x and z axes.

	Args:
	obj1 (bpy.types.Object): The first object.
	obj2 (bpy.types.Object): The second object.

	Returns:
	bool: True if object1 is inside object2 on the x and z axes, False otherwise.
	"""

	# Get the dimensions and world space locations of both objects
	dim1 = obj1.dimensions
	loc1 = obj1.matrix_world.translation
	dim2 = obj2.dimensions
	loc2 = obj2.matrix_world.translation

	# Calculate the minimum and maximum points of both objects on the x and z axes
	min1_x = loc1.x - dim1.x / 2
	max1_x = loc1.x + dim1.x / 2
	min1_z = loc1.z - dim1.z / 2
	max1_z = loc1.z + dim1.z / 2
	min2_x = loc2.x - dim2.x / 2
	max2_x = loc2.x + dim2.x / 2
	min2_z = loc2.z - dim2.z / 2
	max2_z = loc2.z + dim2.z / 2

	# Check if the minimum and maximum points of object1 are within the minimum and maximum points of object2 on the x and z axes
	if min1_x >= min2_x and max1_x <= max2_x and min1_z >= min2_z and max1_z <= max2_z:
		return True
	else:
		return False


def calc_overlap(obj1, obj2):
	dim1 = obj1.dimensions
	loc1 = obj1.location
	dim2 = obj2.dimensions
	loc2 = obj2.location
	min1 = loc1 - dim1 / 2
	max1 = loc1 + dim1 / 2
	min2 = loc2 - dim2 / 2
	max2 = loc2 + dim2 / 2
	if (min1.x <= max2.x and max1.x >= min2.x and
		min1.y <= max2.y and max1.y >= min2.y and
		min1.z <= max2.z and max1.z >= min2.z):
		return True
	else:
		return False

def make_grease_layers(ob):
	mlayers = {
		'head': ob.data.layers.new('head'),
		'body': ob.data.layers.new('body'),
		'arm.L': ob.data.layers.new('arm.L'),
		'arm.R': ob.data.layers.new('arm.R'),

	}
	for l in mlayers.values():
		l.frames.new(1)

	rem = []
	for stroke in ob.data.layers[0].frames[0].strokes:
		ax,ay,az = calc_avg_points(stroke)
		if az > 1:
			s = mlayers['head'].frames[0].strokes.new()
			copy_stroke(s, stroke)
			rem.append(stroke)
		elif az > -1:
			if ax < -1:
				s = mlayers['arm.R'].frames[0].strokes.new()
				copy_stroke(s, stroke)
				rem.append(stroke)
			elif ax > 1:
				s = mlayers['arm.L'].frames[0].strokes.new()
				copy_stroke(s, stroke)
				rem.append(stroke)

	for s in rem:
		ob.data.layers[0].frames[0].strokes.remove(s)

def copy_stroke(s, stroke):
	s.points.add(len(stroke.points))
	for i in range(len(stroke.points)):
		s.points[i].co = stroke.points[i].co
		s.points[i].strength = stroke.points[i].strength
		s.points[i].pressure = stroke.points[i].pressure
		s.points[i].vertex_color = stroke.points[i].vertex_color

	s.material_index = stroke.material_index
	s.line_width     = stroke.line_width
	s.display_mode   = stroke.display_mode
	s.use_cyclic     = stroke.use_cyclic
	s.vertex_color_fill = stroke.vertex_color_fill

def calc_width_height(points):
	if len(points) < 2: return 0, 0  # At least two points are needed
	# Find the minimum and maximum x and y values
	min_x = min(point.co.x for point in points)
	max_x = max(point.co.x for point in points)
	min_y = min(point.co.z for point in points)
	max_y = max(point.co.z for point in points)  
	# Calculate the width and height
	width = max_x - min_x
	height = max_y - min_y
	return width, height

def calc_avg_points(stroke):
	x = y = z = 0.0
	for p in stroke.points:
		x+=p.co.x
		y+=p.co.y
		z+=p.co.z
	x /= len(stroke.points)
	y /= len(stroke.points)
	z /= len(stroke.points)
	return (x,y,z)

hex2rgb = lambda hx: (int(hx[0:2],16),int(hx[2:4],16),int(hx[4:6],16))

def bpy_make_rect(x,y, width, height, scale=0.01):
	mesh_data = bpy.data.meshes.new("Rectangle")
	#mesh_data.from_pydata(
	#	[
	#	(x, 0, y),
	#	(x + width, 0, y),
	#	(x + width, 0, y + height),
	#	(x, 0, y + height)
	#	],
	#	[],
	#	[(0, 1, 2, 3)]
	#)

	y = -y
	mesh_data.from_pydata(
	[
	(x, 0, y - height),
	(x + width, 0, y - height),
	(x + width, 0, y),
	(x, 0, y)
	],
	[],
	[(0, 1, 2, 3)]
	)

	mesh_data.update()
	obj = bpy.data.objects.new("Rectangle", mesh_data)
	for v in obj.data.vertices:
		v.co *= scale
	bpy.context.scene.collection.objects.link(obj)
	return obj

## for grease pencil object imported from svg
def depth_faker(ob, lstep = 0.01, sstep  = 0.01):
	f = 0.0
	for layer in ob.data.layers:
		for frame in layer.frames:
			for stroke in frame.strokes:
				for point in stroke.points:
					point.co.y -= f
				f += sstep
		f += lstep


def parse_kra(kra, verbose=False, blender_curves=False):
	kra_fname = os.path.split(kra)[-1]
	arc = zipfile.ZipFile(kra,'r')
	print(arc)
	dump = {'layers':[]}
	groups = {}
	layers = {}
	bobs = []

	for f in arc.filelist:
		if verbose: print(f)
		#files.append(f.filename)
		if '/layers/' in f.filename:
			a = f.filename.split('/layers/')[-1]
			print(a)
			tag = a.split('.')[0]
			if tag not in layers:
				layers[tag] = []
			layers[tag].append(f.filename)

	if verbose: print(layers)

	x = arc.read('documentinfo.xml')
	if verbose:
		print('-'*80)
		print(x.decode('utf-8'))
		print('-'*80)
	info = xml.dom.minidom.parseString(x)
	print(info)


	x = arc.read('maindoc.xml')
	if verbose:
		print('-'*80)
		print(x.decode('utf-8'))
		print('-'*80)
	doc = xml.dom.minidom.parseString(x)
	print(doc)

	IMAGE = doc.getElementsByTagName('IMAGE')[0]
	width = int(IMAGE.getAttribute('width'))
	height = int(IMAGE.getAttribute('height'))
	title = IMAGE.getAttribute('name')

	## allows for python logic to be put in a krita description,
	## only if the user renames the title of the document so that
	## it ends with .py, then it will be run in blender python.
	if title.endswith('.py'):
		#sub = IMAGE.getAttribute('description')  ## always empty?
		pyscript = info.getElementsByTagName('abstract')[0]
		pyscript = pyscript.firstChild.nodeValue
	else:
		pyscript = None

	bprops = info.getElementsByTagName('keyword')
	if bprops and bprops[0].firstChild:
		bprops = bprops[0].firstChild.nodeValue.split()
	else:
		bprops = None

	pixlayers = []
	reflayers = []
	obscripts = {}
	gscripts  = {}
	xlayers = {}
	for layer in doc.getElementsByTagName('layer'):
		print(layer.toxml())
		ob = parent = None
		x = int(layer.getAttribute('x'))
		y = int(layer.getAttribute('y'))
		tag = layer.getAttribute('filename')
		xlayers[tag] = layer

		## check if parent layer is a group
		if layer.parentNode and layer.parentNode.tagName == 'layers':
			if layer.parentNode.parentNode.tagName=='IMAGE':
				print('root layer:', layer)
			elif layer.parentNode.parentNode.tagName=='layer':
				g = layer.parentNode.parentNode
				print('layer parent:', g)
				parent = groups[g.getAttribute('name')]['root']

		if layer.getAttribute('nodetype')=='grouplayer':
			if bpy:
				bpy.ops.object.empty_add(type="CIRCLE")
				ob = bpy.context.active_object
				ob.name = layer.getAttribute('name')
				bobs.append(ob)
				ob.location.x = (x-(width/2)) * 0.01
				ob.location.z = -(y-(height/2)) * 0.01 

			groups[layer.getAttribute('name')] = {
				'x': int(layer.getAttribute('x')),
				'y': int(layer.getAttribute('y')),
				'children':[],
				'root':ob,
			}

		elif layer.getAttribute('nodetype')=='shapelayer':
			svg = arc.read( layers[tag][0] ).decode('utf-8')
			print(svg)
			dump['layers'].append(svg)
			if bpy:
				svgtmp = '/tmp/__krita2blender__.svg'
				open(svgtmp,'w').write(svg)
				if blender_curves:
					bpy.ops.import_curve.svg(filepath=svgtmp)
					ob = bpy.context.active_object  ## TODO this is not correct?
					ob.name = layer.getAttribute('name') + '.CURVE'
					ob.scale *= 100
					bobs.append(ob)
				bpy.ops.wm.gpencil_import_svg(filepath=svgtmp, scale=100, resolution=5)
				ob = bpy.context.active_object
				ob.name = layer.getAttribute('name')
				bobs.append(ob)
		elif layer.getAttribute('nodetype')=='paintlayer':
			if not int(layer.getAttribute('visible')):
				print('skip layer:', tag)
			else:
				pixlayers.append( tag )
		elif layer.getAttribute('nodetype')=='filelayer':
			src = layer.getAttribute('source')
			assert os.path.isfile(src)
			reflayers.append( {'source':src, 'x':x, 'y':y} )
			if src.endswith('.svg'):
				bobs += parse_svg( src, gscripts, x=x, y=y, kra_fname=kra_fname )

			if bpy:
				if src.endswith('.kra'):
					## nested kra
					bpy.ops.object.empty_add(type="SINGLE_ARROW")
					ob = bpy.context.active_object
					ob.name = src
					bobs.append(ob)
					ob['KRITA'] = src
					if parent:
						ob.location.x = x * 0.01
						ob.location.z = -y * 0.01 
					else:
						ob.location.x = (x-(width/2)) * 0.01
						ob.location.z = -(y-(height/2)) * 0.01
				elif src.endswith(('.png', '.jpg', '.webp', '.tga', '.tif', '.bmp')):
					bpy.ops.object.empty_add(type="IMAGE")
					ob = bpy.context.active_object
					bobs.append(ob)
					img = bpy.data.images.load(src)
					ob.data = img
					ob.location.x = (x-(width/2)) * 0.01
					ob.location.z = -(y-(height/2)) * 0.01 
					ob.rotation_euler.x = math.pi/2
					ob.scale.x = img.width * 0.01
					ob.scale.y = img.height * 0.01
		if bpy and parent:
			ob.parent = parent

	while pixlayers:
		tag = pixlayers.pop()
		print('saving pixel layer:', tag)
		tmp = '/tmp/tmp.kra'
		aout = zipfile.ZipFile(tmp,'w')

		root = doc.getElementsByTagName('layers')[0]
		while root.firstChild: root.removeChild(root.firstChild)
		root.appendChild( xlayers[tag] )

		aout.writestr('maindoc.xml', doc.toxml())
		for f in layers[tag]:
			print(f)
			aout.writestr(
				f, arc.read(f)
			)

		print(aout.filelist)
		aout.close()

		cmd = ['krita', '--export', '--export-filename', '/tmp/%s.png' % tag, tmp]
		print(cmd)
		subprocess.check_call(cmd)

		if bpy:
			print(xlayers[tag].toxml())
			bpy.ops.object.empty_add(type="IMAGE")
			ob = bpy.context.active_object
			bobs.append(ob)
			img = bpy.data.images.load('/tmp/%s.png' % tag)
			ob.data = img
			ob.location.y = len(pixlayers) * 0.001 * height
			ob.name = xlayers[tag].getAttribute('name')
			ob.rotation_euler.x = math.pi/2
			ob.scale.x = width * 0.01
			ob.scale.y = height * 0.01

	if bpy:
		col = bpy.data.collections.new(kra_fname)
		bpy.context.scene.collection.children.link(col)

		bpy.ops.object.empty_add(type="ARROWS")
		root = bpy.context.active_object
		col.objects.link(root)
		for o in bobs:
			if not o.parent:
				o.parent = root
			col.objects.link(o)

		if bprops:
			for p in bprops:
				v = 0.0
				if '=' in p:
					n,v = p.split('=')
					try: v = float(v)
					except: pass
				else:
					n = p
				root[n] = float(v)



	if bpy and pyscript:
		scope = {'bpy':bpy, 'random':random, 'uniform':uniform, 'self':root}
		gen = []
		for ob in bobs:
			scope[ safename(ob.name) ] = ob
			gen.append('%s = bpy.data.objects["%s"]' % (safename(ob.name), ob.name))
		print('exec script:')
		print(pyscript)
		gen.append(pyscript)
		txt = bpy.data.texts.new(name='__krita2blender__.py')
		#txt.from_string(PYHEADER + '\n'.join(gen))
		#exec(pyscript, scope)
		txt.from_string(pyscript)
		SCRIPTS.append({'scope':scope, 'script':txt})

	else:
		print('user python script:', pyscript)

	if bpy:
		return col
	else:
		return dump

PYHEADER = '''
import bpy, mathutils
from random import random, uniform
'''

def safename(n):
	import string
	nope = string.punctuation + string.whitespace
	for c in nope:
		n = n.replace(c,'_')
	return n

JSONS = []
REN_OUTPUT = None
if __name__ == "__main__":
	run_blender = False
	blender_ren = False
	kras = []
	svgs = []
	output = None
	do_strip = False
	for arg in sys.argv:
		if arg.startswith('--output='):
			output = arg.split('=')[-1]
		elif arg.startswith('--ren-out='):
			REN_OUTPUT = arg.split('=')[-1]
		elif arg.endswith('.kra'):
			kras.append(arg)
		elif arg.endswith('.svg'):
			svgs.append(arg)
		elif arg.endswith('.json'):
			JSONS.append(arg)
		elif arg=='--blender':
			run_blender=True
		elif arg=='--strip':
			do_strip = True
		elif arg=='--render':
			blender_ren = True

	if do_strip:
		if not output:
			print('error: output=FILE is required with --strip')
			raise RuntimeError('invalid command line args with option --strip: %s' % sys.argv)
		elif not kras:
			print('error: input .kra file required with --strip')
			raise RuntimeError('invalid command line args with option --strip: %s' % sys.argv)

		kra = kras[0]
		assert output != kra

		krain = zipfile.ZipFile(kra,'r')
		kraout = zipfile.ZipFile(output, 'w')
		for f in krain.filelist:
			if f.filename=='mergedimage.png':
				print('skipping', f)
				continue
			print('saving:', f)
			kraout.writestr(f, krain.read(f.filename))
		print('saving stripped:', output)
		kraout.close()
		sys.exit()
	elif run_blender:
		cmd = ['blender']
		if blender_ren: cmd.append('--background')
		cmd += ['--python', __file__]
		if kras or svgs or JSONS or blender_ren: cmd.append('--')
		if kras: cmd += kras
		if svgs: cmd += svgs
		if JSONS: cmd += JSONS
		if blender_ren:
			assert sys.argv[-1].endswith('.png')
			cmd.append('--ren-out=%s' % sys.argv[-1])
		print(cmd)
		subprocess.check_call(cmd)
	elif svgs:
		for s in svgs:
			parse_svg(s, {})
	elif kras:
		for kra in kras:
			a = parse_kra( kra, verbose='--verbose' in sys.argv )
	elif bpy:
		pass
	else:
		print('no krita .kra files given')


## in blender below this point ##
if not bpy: sys.exit()
from bpy_extras.io_utils import ImportHelper
import mathutils


@bpy.utils.register_class
class Ink3dBlender(bpy.types.Operator):
	bl_idname = 'svg2blender.render_svg'
	bl_label  = 'Render SVG (.svg)'
	def execute(self, context):
		render_svg()
		return {'FINISHED'}

@bpy.utils.register_class
class Inkscape4Blender(bpy.types.Operator, ImportHelper):
	bl_idname = 'svg2blender.import_svg'
	bl_label  = 'Import Inkscape SVG (.svg)'
	filter_glob : bpy.props.StringProperty(default='*.svg')
	def execute(self, context):
		parse_svg(self.filepath)
		return {'FINISHED'}


@bpy.utils.register_class
class Krita4Blender(bpy.types.Operator, ImportHelper):
	bl_idname = 'svg2blender.import_kra'
	bl_label  = 'Import Krita File (.kra)'
	filter_glob : bpy.props.StringProperty(default='*.kra')
	def execute(self, context):
		parse_kra(self.filepath)
		return {'FINISHED'}

@bpy.utils.register_class
class Ink3dWorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_Ink3dWorld_Panel"
	bl_label = "Ink3D"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"
	def draw(self, context):
		self.layout.operator("svg2blender.import_kra")
		self.layout.operator("svg2blender.import_svg")
		self.layout.operator("svg2blender.render_svg")

def on_up_arrow(evt):
	ob = bpy.context.active_object
	if not ob: return
	ob.location.y += 0.1
def on_down_arrow(evt):
	ob = bpy.context.active_object
	if not ob: return
	ob.location.y -= 0.1
def on_left_arrow(evt):
	ob = bpy.context.active_object
	if not ob: return
	ob.rotation_euler.z += 0.1
	if ob.rotation_euler.z > math.pi/2:
		ob.rotation_euler.z = math.pi / 2
def on_right_arrow(evt):
	ob = bpy.context.active_object
	if not ob: return
	ob.rotation_euler.z -= 0.1
	if ob.rotation_euler.z < -math.pi/2:
		ob.rotation_euler.z = -math.pi / 2
def on_home(evt):
	ob = bpy.context.active_object
	if not ob: return
	ob.rotation_euler.z = 0
def on_page_up(evt):
	ob = bpy.context.active_object
	if not ob and not ob.type=='MESH': return
	if not '__DEPTH__' in ob.modifiers: return
	ob.modifiers['__DEPTH__'].thickness += 0.1
def on_page_down(evt):
	ob = bpy.context.active_object
	if not ob and not ob.type=='MESH': return
	if not '__DEPTH__' in ob.modifiers: return
	ob.modifiers['__DEPTH__'].thickness -= 0.1

def on_a(evt):
	if not GameSim['bots']: return
	bot = GameSim['bots'][0]
	bot['root'].location.x -= 0.2
	if bot['leg_roots']:
		for o in bot['leg_roots']:
			o.rotation_euler.y = uniform(-0.4,0.4)

def on_d(evt):
	if not GameSim['bots']: return
	bot = GameSim['bots'][0]
	bot['root'].location.x += 0.2
	if bot['leg_roots']:
		for o in bot['leg_roots']:
			o.rotation_euler.y = uniform(-0.4,0.4)

def on_w(evt):
	if not GameSim['bots']: return
	bot = GameSim['bots'][0]
	bot['root'].location.y += 0.2
	if bot['leg_roots']:
		bot['jump'] += 0.1
		for o in bot['leg_roots']:
			o.rotation_euler.x = uniform(-0.4,0.4)

def on_s(evt):
	if not GameSim['bots']: return
	bot = GameSim['bots'][0]
	bot['root'].location.y -= 0.2
	if bot['leg_roots']:
		bot['jump'] += 0.1
		for o in bot['leg_roots']:
			o.rotation_euler.x = uniform(-0.4,0.4)

GameSim['hotkeys'] = {
	'A': on_a, 'W':on_w, 'S':on_s, 'D':on_d,
	'UP_ARROW' : on_up_arrow,
	'DOWN_ARROW' : on_down_arrow,
	'LEFT_ARROW' : on_left_arrow,
	'RIGHT_ARROW' : on_right_arrow,
	'HOME': on_home,
	'PAGE_UP' : on_page_up,
	'PAGE_DOWN' : on_page_down,
}

_lazy_loads = {}
_timer = None
@bpy.utils.register_class
class Svg2BlenderOperator(bpy.types.Operator):
	"Svg2Blender Python Scripts"
	bl_idname = "svg2blender.run"
	bl_label = "svg2blender_run"
	bl_options = {'REGISTER'}
	def modal(self, context, event):
		if event.type in GameSim['hotkeys']:
			GameSim['hotkeys'][event.type](event)
			return {'RUNNING_MODAL'}
		elif event.type == "TIMER":
			for o in bpy.data.objects:
				if 'KRITA' in o.keys():
					kra = o['KRITA']
					if not kra: continue
					if kra not in _lazy_loads:
						col = parse_kra(kra)
						_lazy_loads[kra] = col
					o.instance_type = 'COLLECTION'
					o.instance_collection = _lazy_loads[kra]
					o['KRITA']=None

			for s in SCRIPTS:
				scope  = s['scope']
				script = s['script'].as_string()
				exec(script, scope, scope)

			for bot in GameSim['bots']:
				if bot['jump']:
					bot['root'].location.z += bot['jump']
					bot['jump'] *= 0.5
				bot['root'].location.z *= 0.7
				if 'neck' in bot and random() < 0.05:
					bot['neck'].rotation_euler.y = uniform(-1,0.2)


			for eye in GameSim['eyes']:
				if random() < 0.1:
					eye.scale.z = random() * 0.05
				else:
					eye.scale.z = 1.0

			for head in GameSim['heads']:
				if random() < 0.05:
					head.rotation_euler.y = uniform(-0.1,0.1)

		return {'PASS_THROUGH'} # will not supress event bubbles

	def invoke (self, context, event):
		global _timer
		if _timer is None:
			_timer = self._timer = context.window_manager.event_timer_add(
				time_step=0.025,
				window=context.window
			)
			context.window_manager.modal_handler_add(self)
			return {'RUNNING_MODAL'}
		return {'FINISHED'}

	def execute (self, context):
		return self.invoke(context, None)


def on_blend_save(blend):
	print('USER saved blend file:', blend)
	dump = {}
	for ob in bpy.data.objects:
		if '__Y__' in ob.keys():
			d = {}
			if ob['__Y__'] != ob.location.y:
				d['y'] = ob.location.y
			if ob['__X__'] != ob.location.x:
				d['x'] = ob.location.x
			if ob['__RZ__'] != ob.rotation_euler.z:
				d['rz'] = ob.rotation_euler.z
			if '__DEPTH__' in ob.modifiers:
				if ob['depth'] != ob.modifiers['__DEPTH__'].thickness:
					d['depth'] = ob.modifiers['__DEPTH__'].thickness
			if d:
				dump[ob.name]=d

	print('json dump:', dump)
	open('/tmp/__inkscape__.json','w').write(json.dumps(dump))

def ink3d_render(out, fast=True, pixelated=True):
	if fast:
		bpy.context.scene.eevee.taa_samples = 1
		bpy.context.scene.eevee.taa_render_samples = 1
		bpy.context.scene.eevee.use_taa_reprojection = False
	if pixelated:
		bpy.context.scene.grease_pencil_settings.antialias_threshold = 0.0

	bpy.context.scene.render.film_transparent = True
	bpy.context.scene.render.image_settings.color_mode = 'RGBA'
	bpy.context.scene.render.filepath=out
	bpy.context.scene.render.resolution_x = 512
	bpy.context.scene.render.resolution_y = 512
	bpy.ops.render.render(animation=False, write_still=True)

def render_svg(out='/tmp/__b2svg__.svg', debug=1):
	for ob in bpy.data.objects:
		if not ob.type=='GPENCIL': continue
		bpy.ops.object.select_all(action='DESELECT')
		ob.select_set(True)
		bpy.context.view_layer.objects.active = ob
		tmp = '/tmp/__%s__.svg' % ob.name
		bpy.ops.wm.gpencil_export_svg(
			filepath=tmp, use_fill=True, stroke_sample=1, check_existing=False,
			use_normalized_thickness=False, selected_object_type='ACTIVE',
		)
		os.system('cat %s' % tmp)
		svg = open(tmp).read()
		assert '<?xml?>' in svg
		## eye-of-gnome says: XML parse error: Error domain 1 code 64 on line 3
		## data: XML declaration allowed only at the start of the document
		if debug > 1:
			open(tmp,'w').write(svg.split('<?xml?>')[-1])
			os.system('eog %s' % tmp)

		svg = xml.dom.minidom.parseString(svg.split('<?xml?>')[-1])
		for elt in svg.getElementsByTagName('polyline'):
			sw = float( elt.getAttribute('stroke-width') )
			sw *= 0.05
			elt.setAttribute('stroke-width', str(sw) )

		open(tmp,'w').write(svg.toprettyxml())
		if debug:
			os.system('eog %s' % tmp)

if __name__=='__main__':
	bpy.context.preferences.view.show_splash = False
	bpy.ops.wm.save_as_mainfile(filepath="/tmp/__inkscape__.blend")
	bpy.app.handlers.save_post.append(on_blend_save)
	if 'Cube' in bpy.data.objects:
		bpy.data.objects['Cube'].hide_set(True)
		bpy.data.objects['Cube'].hide_render=True
	if REN_OUTPUT:
		print('headless mode')
		ink3d_render(REN_OUTPUT)
	else:
		bpy.ops.svg2blender.run()
