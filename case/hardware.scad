// HAUKI hardware model: Raspberry Pi 1A+, Waveshare 2.13" e-Paper HAT V4 and panel.
// Not printable. It is the reference the case is designed around.
//
// Frame: wall-mounted orientation seen from the front. Origin at the Pi's lower left
// corner, on the underside of the board. +X right, +Y up, +Z out of the wall.
//
// Sources: [D] Pi A+ mechanical drawing, [S] V4 panel specification p.6, [M] measured on
// the real parts, [A] assumed, correct from test prints.

/* [Pi] */
pi_w = 65;              // [D]
pi_h = 56;              // [D]
pi_t = 1.3;             // [M]
pi_corner_r = 3;        // [D]
pi_hole_d = 2.75;       // [D]
pi_hole_inset = 3.5;    // [D]

header_cx = pi_w / 2;   // [D] 29 mm from the left hole
header_cy = pi_h - pi_hole_inset;
header_l = 51;          // [D] scaled
header_w = 5;           // [D] scaled
header_z = 8.5;         // [D] above the board

/* [Ports] */
usb_power_cx = 10.6;    // [D]
usb_power_top = 4.3;    // [M] from the underside of the board
usb_a_cy = 31.45;       // [D]
usb_a_top = 9.3;        // [M] from the underside; the drawing implies 8.4
hdmi_cx = 32;           // [D]
hdmi_z = 6.5;           // [D] above the board
audio_cx = pi_w - 11.5; // [D]
audio_z = 6;            // [D] above the board

/* [HAT] */
hat_w = 65;             // published
hat_h = 30.2;           // published
hat_t = 1.6;            // [A]
hat_gap_top = 9;        // [M] HAT underside to Pi top surface, at the header end
hat_gap_bottom = 11.3;  // [M] same, at the free end; the tilt is intentional
hat_inset_x = 0;        // [A] flush with the Pi's left edge
hat_inset_top = 0;      // [A] flush with the Pi's top edge
socket_h = 8.8;         // [A] the plastic socket that rests on the Pi

/* [Panel] */
glass_w = 59.2;         // [S]
glass_h = 29.2;         // [S]
glass_t = 1;            // [S]
glass_gap = 0;          // [A] between HAT and glass
glass_inset_x = (hat_w - glass_w) / 2;  // [M] about 3 mm on both sides
glass_inset_y = (hat_h - glass_h) / 2;  // [M] about at the HAT's edges
// Distances from the glass edges; the ribbon end is on the left
aa_w = 48.55;           // [S] active area, the pixels
aa_h = 23.70;           // [S]
aa_inset_ribbon = 8.4;  // [S]
aa_inset_top = 3.25;    // [S] which long edge this belongs to is inferred
va_margin = 0.4;        // [S] viewing area beyond the active area on each side
ribbon_w = 13;          // [A]

/* [Dongle] */
// Placeholder, the fit is worked out from test prints
dongle_l = 20;
dongle_w = 16;
dongle_t = 9;

$fn = 48;
eps = 0.02;

hat_angle = asin((hat_gap_bottom - hat_gap_top) / hat_h);

// Moves a part from the HAT's frame into the Pi's. In the HAT's frame the origin is the
// upper left corner of its underside, and the board runs towards -Y.
module on_hat() {
    translate([hat_inset_x, pi_h - hat_inset_top, pi_t + hat_gap_top])
        rotate([-hat_angle, 0, 0])
            children();
}

function hat_z(y) = pi_t + hat_gap_top + (pi_h - hat_inset_top - y) * tan(hat_angle);

module rounded_plate(w, h, t, r) {
    linear_extrude(t)
        translate([r, r])
            offset(r)
                square([w - 2 * r, h - 2 * r]);
}

module pi_board() {
    color("seagreen")
        difference() {
            rounded_plate(pi_w, pi_h, pi_t, pi_corner_r);
            for (x = [pi_hole_inset, pi_w - pi_hole_inset], y = [pi_hole_inset, pi_h - pi_hole_inset])
                translate([x, y, -1])
                    cylinder(d = pi_hole_d, h = pi_t + 2);
        }
}

// The sizes of the ports and chips are scaled from the drawing, their overhangs included
module pi_parts() {
    color("gold")
        translate([header_cx - header_l / 2, header_cy - header_w / 2, pi_t])
            cube([header_l, header_w, header_z]);

    color("silver") {
        translate([usb_power_cx - 3.9, -1.5, pi_t])
            cube([7.8, 6.2, usb_power_top - pi_t]);
        translate([pi_w - 12, usb_a_cy - 6.75, pi_t])
            cube([14, 13.5, usb_a_top - pi_t]);
        translate([hdmi_cx - 7.25, -1.5, pi_t])
            cube([14.5, 12, hdmi_z]);
    }

    color("dimgray") {
        translate([audio_cx - 3.6, 0, pi_t])
            cube([7.2, 12.4, audio_z]);
        translate([audio_cx, 0, pi_t + 3])
            rotate([90, 0, 0])
                cylinder(d = 6, h = 3);
        // Camera and display connectors
        translate([43.5, 0.5, pi_t])
            cube([3.5, 22, 5.5]);
        translate([2.6, 17, pi_t])
            cube([2.6, 22, 5.5]);
        // SoC
        translate([20, 24, pi_t])
            cube([14, 14, 1.2]);
    }

    // microSD on the underside of the left edge, not in the drawing
    color("dimgray")
        translate([0, 28 - 7, -1.5])
            cube([15, 14, 1.5]);
    color("royalblue")
        translate([-2.5, 28 - 5.5, -1.2])
            cube([15, 11, 0.8]);
}

module dongle() {
    color("white")
        translate([pi_w + 2, usb_a_cy - dongle_w / 2, (pi_t + usb_a_top) / 2 - dongle_t / 2])
            cube([dongle_l, dongle_w, dongle_t]);
}

module hat() {
    color("steelblue")
        translate([0, -hat_h, 0])
            cube([hat_w, hat_h, hat_t]);
    // The socket reaches down onto the Pi
    color("black")
        translate([header_cx - hat_inset_x - (header_l + 1) / 2, -(pi_h - hat_inset_top - header_cy) - (header_w + 1) / 2, -socket_h])
            cube([header_l + 1, header_w + 1, socket_h]);
}

module panel() {
    z0 = hat_t + glass_gap;
    x0 = glass_inset_x;
    y0 = -hat_h + glass_inset_y;
    aa_x = x0 + aa_inset_ribbon;
    aa_y = y0 + glass_h - aa_inset_top - aa_h;

    color("whitesmoke")
        translate([x0, y0, z0])
            cube([glass_w, glass_h, glass_t]);
    color("lightgray")
        translate([aa_x - va_margin, aa_y - va_margin, z0 + glass_t])
            cube([aa_w + 2 * va_margin, aa_h + 2 * va_margin, eps]);
    color("gainsboro")
        translate([aa_x, aa_y, z0 + glass_t + eps])
            cube([aa_w, aa_h, eps]);
    // The ribbon wraps around the HAT's left edge to its underside
    color("darkorange")
        translate([-0.3, y0 + (glass_h - ribbon_w) / 2, 0]) {
            translate([0, 0, hat_t])
                cube([x0 + 0.3, ribbon_w, 0.3]);
            translate([0, 0, -0.3])
                cube([0.3, ribbon_w, hat_t + 0.6]);
            translate([0, 0, -0.3])
                cube([5, ribbon_w, 0.3]);
        }
}

module hardware() {
    pi_board();
    pi_parts();
    dongle();
    on_hat() {
        hat();
        panel();
    }
}

// case.scad includes this file and sets this to false
show_hardware = true;

if (show_hardware)
    hardware();

echo(hat_angle = hat_angle);
echo(usb_a_clearance_to_hat = hat_z(usb_a_cy + 6.75) - usb_a_top);
echo(header_clearance_to_hat = hat_z(header_cy + header_w / 2) - (pi_t + header_z));
echo(panel_front_at_top = hat_z(pi_h - hat_inset_top) + (hat_t + glass_gap + glass_t) / cos(hat_angle));
echo(panel_front_at_bottom = hat_z(pi_h - hat_inset_top - hat_h * cos(hat_angle)) + (hat_t + glass_gap + glass_t) / cos(hat_angle));
