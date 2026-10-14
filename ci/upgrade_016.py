#!/usr/bin/env python3
"""CI-only overlay for the v0.16 source snapshot. Applies on extraction of v0.15."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def replace(path,old,new):
    p=root/path
    s=p.read_text()
    if old not in s:
        raise RuntimeError(f"Expected source fragment not found: {path}")
    p.write_text(s.replace(old,new))

src="src/main/java/dev/dalmacc/godbridge/TargetFinder.java"
replace(src,
    "    private static boolean rayHitsFace(Minecraft mc, Vec3 eye, BlockPos anchor, Direction side, Vec3 point) {",
    """    /** Extend the line of sight THROUGH the target along eye -> surface point.
     * A normal-only inward offset raises the side-plane intersection above the top
     * edge when the spot is near y=1 and the player looks sharply downward. */
    static Vec3 rayEndThroughTarget(Vec3 eye, Vec3 surfacePoint) {
        Vec3 direction = surfacePoint.subtract(eye);
        double distance = direction.length();
        if (distance < 1.0e-8) return surfacePoint;
        return surfacePoint.add(direction.scale(0.125 / distance));
    }

    private static boolean rayHitsFace(Minecraft mc, Vec3 eye, BlockPos anchor, Direction side, Vec3 point) {""")
replace(src,
    "Vec3 rayEnd = point.subtract(side.getStepX() * 0.09, 0, side.getStepZ() * 0.09);",
    "Vec3 rayEnd = rayEndThroughTarget(eye, point);")
replace("build.gradle",
    "'GuideGeometrySelfTest',",
    "'GuideGeometrySelfTest', 'TargetRayGeometrySelfTest',")
replace("gradle.properties","mod_version=0.15.0","mod_version=0.16.0")
hud=root/"src/main/java/dev/dalmacc/godbridge/TrainerHud.java"
h=hud.read_text()
for v in ("0.14","0.15"):
    h=h.replace("v"+v,"v0.16").replace("GB "+v,"GB 0.16")
hud.write_text(h)
for rel in ("build.sh","build.ps1",".github/workflows/build.yml"):
    p=root/rel
    text=p.read_text()
    for v in ("0.14.0","0.15.0"):
        text=text.replace("godbridge-trainer-26.3-"+v+".jar",
                          "godbridge-trainer-26.3-0.16.0.jar")
    if rel.endswith("build.yml"):
        text=text.replace('"version": "0.15.0"', '"version": "0.16.0"')
    p.write_text(text)

test=root/"src/test/java/dev/dalmacc/godbridge/TargetRayGeometrySelfTest.java"
test.write_text("""package dev.dalmacc.godbridge;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.Vec3;

/** Regression: high weak spots must be visible along steep viewing rays. */
public final class TargetRayGeometrySelfTest {
    private static void close(double expected, double actual, String note) {
        if (Math.abs(actual - expected) > 1e-8)
            throw new AssertionError(note + ": " + actual + " != " + expected);
    }
    private static Vec3 atPlane(Vec3 eye, Vec3 end, Vec3 point, Direction face) {
        boolean x = face.getAxis() == Direction.Axis.X;
        double a = x ? eye.x : eye.z;
        double b = x ? end.x : end.z;
        double c = x ? point.x : point.z;
        double t = (c-a)/(b-a);
        if (t <= 0 || t >= 1) throw new AssertionError("No crossing " + face);
        return eye.add(end.subtract(eye).scale(t));
    }
    public static void main(String[] args) {
        BlockPos anchor = new BlockPos(0, 300, 0);
        for (Direction face : new Direction[]{Direction.NORTH,Direction.SOUTH,
                Direction.EAST,Direction.WEST}) {
            for (double h : new double[]{0.70,0.89,0.96875,0.99}) {
                Vec3 point = GuideTarget.guidePoint(anchor, face, 0.5, h);
                Vec3 eye = point.add(face.getStepX()*1.5,1.65,face.getStepZ()*1.5);
                Vec3 crossing = atPlane(eye,TargetFinder.rayEndThroughTarget(eye,point),point,face);
                close(point.x,crossing.x,"X");
                close(point.y,crossing.y,"Y");
                close(point.z,crossing.z,"Z");
                if(crossing.y >= 301.0) throw new AssertionError("Above face");
                if(h == 0.96875) {
                    Vec3 oldEnd=point.subtract(face.getStepX()*0.09,0,face.getStepZ()*0.09);
                    if(atPlane(eye,oldEnd,point,face).y <= 301.0)
                        throw new AssertionError("Old geometry failure was not reproduced");
                }
            }
        }
        System.out.println("TargetRayGeometrySelfTest PASS");
    }
}
""")
print("Applied v0.16 ray fix and 18th regression test to",root)
