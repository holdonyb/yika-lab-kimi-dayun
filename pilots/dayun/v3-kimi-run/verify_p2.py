from pathlib import Path
import sys
import bpy
import json

ROOT = Path(__file__).resolve().parent
kinds = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['bricks','balls','disc']
for kind in kinds:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'p2_{kind}.blend'))
    scene = bpy.context.scene
    cache = scene.rigidbody_world.point_cache
    suffix = 'check' if kind.startswith('disc_study_') else 'validation'
    source = json.loads((ROOT/f'p2_{kind}_{suffix}.json').read_text(encoding='utf-8'))
    expected = {sample['frame']:sample['objects'] for sample in source['samples']}
    errors = []
    minimum = {'value':100.0}
    for frame,objects in expected.items():
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for name,position in objects.items():
            obj = bpy.data.objects[name]
            evaluated = obj.evaluated_get(depsgraph)
            difference = (evaluated.matrix_world.translation-__import__('mathutils').Vector(position)).length
            if difference > .0001:
                errors.append({'frame':frame,'id':name,'error':difference})
            z = min((evaluated.matrix_world @ __import__('mathutils').Vector(corner)).z for corner in evaluated.bound_box)
            if z < minimum['value']:
                minimum = {'value':z,'frame':frame,'id':name}
    targets = [obj for obj in scene.objects if obj.rigid_body and obj.rigid_body.type == 'ACTIVE' and not obj.rigid_body.kinematic]
    animated_targets = [obj.name for obj in targets if obj.animation_data and obj.animation_data.action]
    report = {'scene':kind,'cacheBakedAfterReopen':cache.is_baked,'embeddedCache':not cache.use_disk_cache,
              'checkedFrames':sorted(expected),'cachePositionErrors':errors,
              'dynamicTargetsHaveAuthoredTransformActions':animated_targets,
              'minimumEvaluatedBoundingZ':minimum,
              'note':'Actual reopen and random-access cached transforms, compared with the original simulation samples'}
    (ROOT/f'p2_{kind}_cache_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('P2_REOPEN',kind,'baked',cache.is_baked,'errors',len(errors),'target_actions',animated_targets,flush=True)
    if not cache.is_baked or errors:
        raise RuntimeError('Physics cache did not survive reopening')
