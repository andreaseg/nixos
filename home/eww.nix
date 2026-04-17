{ pkgs, ... }:

{
  home.packages = [ pkgs.eww ];

  xdg.configFile."eww/clock.sh" = {
    executable = true;
    text = ''
      #!/bin/sh
      date '+%H %M %S' | awk '{
        h=$1; m=$2; s=$3;
        pi=3.14159265;
        sec_a  = s * 6 * pi / 180;
        min_a  = (m * 6 + s * 0.1) * pi / 180;
        hour_a = ((h % 12) * 30 + m * 0.5) * pi / 180;
        cx=75; cy=75;
        hx = cx + 35 * sin(hour_a); hy = cy - 35 * cos(hour_a);
        mx = cx + 50 * sin(min_a);  my = cy - 50 * cos(min_a);
        sx = cx + 60 * sin(sec_a);  sy = cy - 60 * cos(sec_a);
        print "<svg width=\"150\" height=\"150\" xmlns=\"http://www.w3.org/2000/svg\">";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\"70\" fill=\"rgba(0,0,0,0.7)\" stroke=\"rgba(255,255,255,0.2)\" stroke-width=\"2\"/>";
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""hx"\" y2=\""hy"\" stroke=\"white\" stroke-width=\"4\" stroke-linecap=\"round\"/>";
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""mx"\" y2=\""my"\" stroke=\"#cdd6f4\" stroke-width=\"3\" stroke-linecap=\"round\"/>";
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""sx"\" y2=\""sy"\" stroke=\"#f38ba8\" stroke-width=\"2\" stroke-linecap=\"round\"/>";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\"4\" fill=\"white\"/>";
        print "</svg>";
      }' > /tmp/eww-clock.svg
      echo "/tmp/eww-clock.svg"
    '';
  };

  xdg.configFile."eww/eww.yuck".text = ''
    (defpoll clock-path :interval "1s" `~/.config/eww/clock.sh`)

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
