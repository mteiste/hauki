// HAUKI wall case: a back tray and a snap-on lid, printed in PLA without supports.
// The hardware itself is modelled in hardware.scad, in the same coordinates.
//
// The tray hangs flat on the wall. The lid's front slopes with the panel, so the case
// is deeper at the bottom and the display faces slightly upward.

include <hardware.scad>
show_hardware = false;

// assembly, exploded, section, back, lid, clash
part = "assembly";

/* [Shell] */
wall = 2;               // assumed, not confirmed by the owner
corner_r = 4;
margin_left = 4;        // Inside the walls, around the Pi's outline
margin_top = 3;
margin_bottom = 4;
pi_lift = 4;            // Pi underside above the tray's floor
seam_z = 12;            // Where tray and lid meet
panel_gap = 0.8;        // Air between the glass and the lid: the lid must never press it

/* [Mounting] */
standoff_d = 6;
pilot_d = 2.2;          // Self-tapping M2.5 from the front, in the lower two holes
peg_d = 2.4;            // The upper two holes sit under the HAT, so they get pegs
peg_h = 3;
keyhole_spacing = 37;
keyhole_y = 42;
keyhole_head_d = 8.5;
keyhole_neck_d = 4.5;
keyhole_travel = 6;

/* [Openings] */
power_w = 14;           // Sized for the plug, fit to be tuned from test prints
power_h = 10;
dongle_open_w = 20;
dongle_open_h = 10.6;
vent_w = 2;
vent_pitch = 5;

/* [Window] */
window_chamfer = 1.3;

/* [Snap-fit] */
clip_w = 10;
clip_t = 1.4;
clip_clearance = 0.2;
clip_hook = 0.9;
clip_bottom_z = 2;      // The arm's tip
clips_left_y = [8, 46]; // Clear of the microSD
clips_right_y = [8, 48]; // Clear of the dongle opening
lip_h = 1.5;
lip_t = 1;

// The case is centred on the display window, so it extends past the Pi on the right
window_w = aa_w + 2 * va_margin;
window_x = glass_inset_x + aa_inset_ribbon - va_margin;
case_cx = window_x + window_w / 2;

// Outline
in_x0 = -margin_left;
in_x1 = 2 * case_cx - in_x0;
in_y0 = -margin_bottom;
in_y1 = pi_h + margin_top;
out_x0 = in_x0 - wall;
out_x1 = in_x1 + wall;
out_y0 = in_y0 - wall;
out_y1 = in_y1 + wall;
floor_z = -pi_lift;
back_z = floor_z - wall;

slope = tan(hat_angle);
panel_top_z = hat_z(pi_h - hat_inset_top) + (hat_t + glass_gap + glass_t) / cos(hat_angle);

function front_in(y) = panel_top_z + panel_gap + (pi_h - y) * slope;
function front_out(y) = front_in(y) + wall;

// Everything below the sloped plane, extruded along X
module below_front(f, x0, x1, z0) {
    y0 = out_y0 - 1;
    y1 = out_y1 + 1;
    translate([x0, 0, 0])
        rotate([90, 0, 90])
            linear_extrude(x1 - x0)
                polygon([[y0, z0], [y1, z0], [y1, f(y1)], [y0, f(y0)]]);
}

module outer_solid() {
    intersection() {
        translate([out_x0, out_y0, back_z])
            rounded_plate(out_x1 - out_x0, out_y1 - out_y0, 40, corner_r);
        below_front(function(y) front_out(y), out_x0 - 1, out_x1 + 1, back_z);
    }
}

module cavity() {
    intersection() {
        translate([in_x0, in_y0, floor_z])
            rounded_plate(in_x1 - in_x0, in_y1 - in_y0, 40, corner_r - wall);
        below_front(function(y) front_in(y), in_x0 - 1, in_x1 + 1, floor_z);
    }
}

module shell() {
    difference() {
        outer_solid();
        cavity();
    }
}

module half_space(z0, z1) {
    translate([out_x0 - 1, out_y0 - 1, z0])
        cube([out_x1 - out_x0 + 2, out_y1 - out_y0 + 2, z1 - z0]);
}

module keyhole() {
    translate([0, 0, back_z - 1])
        linear_extrude(wall + 2)
            union() {
                circle(d = keyhole_head_d);
                hull() {
                    circle(d = keyhole_neck_d);
                    translate([0, keyhole_travel])
                        circle(d = keyhole_neck_d);
                }
            }
}

module clip_slots() {
    z0 = clip_bottom_z + 0.6;
    z1 = z0 + 2.2;
    for (y = clips_left_y)
        translate([out_x0 - 1, y - clip_w / 2 - 0.5, z0])
            cube([wall + 2, clip_w + 1, z1 - z0]);
    for (y = clips_right_y)
        translate([in_x1 - 1, y - clip_w / 2 - 0.5, z0])
            cube([wall + 2, clip_w + 1, z1 - z0]);
}

module openings() {
    // Power, in the bottom wall
    translate([usb_power_cx - power_w / 2, out_y0 - 1, (pi_t + usb_power_top) / 2 - pi_t / 2 - power_h / 2])
        cube([power_w, wall + 2, power_h]);
    // Dongle, in the right wall: it stays outside the case for better reception
    translate([in_x1 - 1, usb_a_cy - dongle_open_w / 2, (pi_t + usb_a_top) / 2 - dongle_open_h / 2])
        cube([wall + 2, dongle_open_w, dongle_open_h]);
    // Vents
    for (x = [28 : vent_pitch : 68])
        translate([x, out_y0 - 1, -1])
            cube([vent_w, wall + 2, 9]);
    for (x = [14 : vent_pitch : 59])
        translate([x, in_y1 - 1, -1])
            cube([vent_w, wall + 2, 9]);
}

module back() {
    difference() {
        union() {
            intersection() {
                shell();
                half_space(back_z - 1, seam_z);
            }
            for (x = [pi_hole_inset, pi_w - pi_hole_inset]) {
                translate([x, pi_hole_inset, floor_z - eps])
                    cylinder(d = standoff_d, h = pi_lift + eps);
                translate([x, pi_h - pi_hole_inset, floor_z - eps])
                    cylinder(d = standoff_d, h = pi_lift + eps);
                translate([x, pi_h - pi_hole_inset, 0])
                    cylinder(d = peg_d, h = peg_h);
            }
        }
        for (x = [pi_hole_inset, pi_w - pi_hole_inset])
            translate([x, pi_hole_inset, floor_z + 0.5])
                cylinder(d = pilot_d, h = pi_lift);
        for (x = [case_cx - keyhole_spacing / 2, case_cx + keyhole_spacing / 2])
            translate([x, keyhole_y, 0])
                keyhole();
        openings();
        clip_slots();
    }
}

module window_rect(grow = 0) {
    y0 = -hat_h + glass_inset_y + glass_h - aa_inset_top - aa_h - va_margin;
    translate([window_x - grow, y0 - grow, 0])
        square([window_w + 2 * grow, aa_h + 2 * va_margin + 2 * grow]);
}

// Made in the HAT's frame, so it stays square to the panel
module window() {
    s = hat_t + glass_gap + glass_t;
    on_hat() {
        translate([0, 0, s + panel_gap / 2])
            linear_extrude(wall + 2)
                window_rect();
        hull() {
            translate([0, 0, s + panel_gap + wall - window_chamfer])
                linear_extrude(eps)
                    window_rect();
            translate([0, 0, s + panel_gap + wall + eps])
                linear_extrude(eps)
                    window_rect(window_chamfer);
        }
    }
}

// One clip on the left side, the arm's outer face against the wall
module clip(y) {
    x = in_x0 + clip_clearance;
    top = front_in(y) + 0.5;
    translate([0, y + clip_w / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(clip_w)
                polygon([
                    [x + clip_t, clip_bottom_z],
                    [x + clip_t, top],
                    [x, top],
                    [x, clip_bottom_z + 1.9],
                    [x - clip_hook, clip_bottom_z + 1.1],
                    [x - clip_hook, clip_bottom_z + 0.9],
                    [x, clip_bottom_z]
                ]);
}

module lip() {
    intersection() {
        difference() {
            translate([in_x0 + clip_clearance, in_y0 + clip_clearance, seam_z - lip_h])
                rounded_plate(in_x1 - in_x0 - 2 * clip_clearance, in_y1 - in_y0 - 2 * clip_clearance, lip_h + 3, corner_r - wall);
            translate([in_x0 + clip_clearance + lip_t, in_y0 + clip_clearance + lip_t, seam_z - lip_h - 1])
                rounded_plate(in_x1 - in_x0 - 2 * (clip_clearance + lip_t), in_y1 - in_y0 - 2 * (clip_clearance + lip_t), lip_h + 5, 1);
        }
        below_front(function(y) front_in(y) + 0.5, in_x0, in_x1, seam_z - lip_h);
    }
}

module lid() {
    difference() {
        intersection() {
            shell();
            half_space(seam_z, 60);
        }
        window();
    }
    lip();
    for (y = clips_left_y)
        clip(y);
    for (y = clips_right_y)
        translate([in_x0 + in_x1, 0, 0])
            mirror([1, 0, 0])
                clip(y);
}

// Lying on the sloped front, so the window edge prints against the bed
module lid_for_print() {
    rotate([180, 0, 0])
        rotate([hat_angle, 0, 0])
            translate([0, -pi_h, -front_out(pi_h)])
                lid();
}

module section_cut() {
    intersection() {
        children();
        translate([32 - 200, -50, -50])
            cube([200, 200, 200]);
    }
}

if (part == "assembly") {
    color("ivory") back();
    color("ivory") lid();
    hardware();
} else if (part == "exploded") {
    color("ivory") back();
    hardware();
    translate([0, 0, 35])
        color("ivory") lid();
} else if (part == "section") {
    section_cut() {
        color("ivory") back();
        color("ivory") lid();
        hardware();
    }
} else if (part == "back") {
    back();
} else if (part == "lid") {
    lid_for_print();
} else if (part == "clash") {
    // The tray is dropped a hair: the Pi touching its standoffs is not a clash
    intersection() {
        union() {
            translate([0, 0, -eps])
                back();
            lid();
        }
        hardware();
    }
}

echo(outer_w = out_x1 - out_x0, outer_h = out_y1 - out_y0, wall_past_pi = out_x1 - pi_w);
echo(depth_top = front_out(out_y1) - back_z, depth_bottom = front_out(out_y0) - back_z);
