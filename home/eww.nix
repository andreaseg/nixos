{ pkgs, ... }:

{
  home.packages = [ pkgs.eww ];

  xdg.configFile."eww/clock.sh" = {
    executable = true;
    text = ''
      #!/bin/sh
      date '+%H %M' | awk '{
        h=$1; m=$2;
        pi=3.14159265;
        min_a  = m * 6 * pi / 180;
        hour_a = ((h % 12) * 30 + m * 0.5) * pi / 180;
        cx=75; cy=75;
        hx = cx + 38 * sin(hour_a); hy = cy - 38 * cos(hour_a);
        mx = cx + 55 * sin(min_a);  my = cy - 55 * cos(min_a);
        print "<svg width=\"150\" height=\"150\" xmlns=\"http://www.w3.org/2000/svg\">";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\"70\" fill=\"none\" stroke=\"rgba(255,255,255,0.3)\" stroke-width=\"1\"/>";
        for (i = 0; i < 12; i++) {
          a = i * 30 * pi / 180;
          x1 = cx + 63 * sin(a); y1 = cy - 63 * cos(a);
          x2 = cx + 70 * sin(a); y2 = cy - 70 * cos(a);
          print "  <line x1=\""x1"\" y1=\""y1"\" x2=\""x2"\" y2=\""y2"\" stroke=\"rgba(255,255,255,0.7)\" stroke-width=\"2\" stroke-linecap=\"round\"/>";
        }
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""hx"\" y2=\""hy"\" stroke=\"white\" stroke-width=\"4\" stroke-linecap=\"round\"/>";
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""mx"\" y2=\""my"\" stroke=\"rgba(255,255,255,0.6)\" stroke-width=\"2\" stroke-linecap=\"round\"/>";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\"3\" fill=\"white\"/>";
        print "</svg>";
      }' > /tmp/eww-clock.svg
      echo "/tmp/eww-clock.svg"
    '';
  };

  xdg.configFile."eww/eww.yuck".text = ''
    (defpoll clock-path :interval "10s" `~/.config/eww/clock.sh`)

    (defwidget clock []
      (image :path clock-path :image-width 150 :image-height 150))

    (defwindow clock
      :monitor 0
      :geometry (geometry
        :x "20px"
        :y "20px"
        :width "150px"
        :height "150px"
        :anchor "top left")
      :stacking "bottom"
      :exclusive false
      (clock))
  '';
}
