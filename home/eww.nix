{ pkgs, ... }:

{
  home.packages = [ pkgs.eww ];

  xdg.configFile."eww/clock.sh" = {
    executable = true;
    text = ''
      #!/bin/sh
      SIZE=320

      date '+%H %M' | awk -v size="$SIZE" '{
        h=$1; m=$2;
        pi=3.14159265;
        min_a  = m * 6 * pi / 180;
        hour_a = ((h % 12) * 30 + m * 0.5) * pi / 180;
        cx = size / 2; cy = size / 2;
        r          = size * 0.46;
        pip_outer  = size * 0.46;
        pip_inner  = size * 0.41;
        hour_len   = size * 0.25;
        min_len    = size * 0.36;
        hx = cx + hour_len * sin(hour_a); hy = cy - hour_len * cos(hour_a);
        mx = cx + min_len  * sin(min_a);  my = cy - min_len  * cos(min_a);
        print "<svg width=\""size"\" height=\""size"\" xmlns=\"http://www.w3.org/2000/svg\">";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\""r"\" fill=\"none\" stroke=\"rgba(255,255,255,0.3)\" stroke-width=\"1\"/>";
        for (i = 0; i < 12; i++) {
          a = i * 30 * pi / 180;
          x1 = cx + pip_inner * sin(a); y1 = cy - pip_inner * cos(a);
          x2 = cx + pip_outer * sin(a); y2 = cy - pip_outer * cos(a);
          print "  <line x1=\""x1"\" y1=\""y1"\" x2=\""x2"\" y2=\""y2"\" stroke=\"rgba(255,255,255,0.7)\" stroke-width=\"2\" stroke-linecap=\"round\"/>";
        }
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""hx"\" y2=\""hy"\" stroke=\"white\" stroke-width=\""size*0.025"\" stroke-linecap=\"round\"/>";
        print "  <line x1=\""cx"\" y1=\""cy"\" x2=\""mx"\" y2=\""my"\" stroke=\"rgba(255,255,255,0.6)\" stroke-width=\""size*0.013"\" stroke-linecap=\"round\"/>";
        print "  <circle cx=\""cx"\" cy=\""cy"\" r=\""size*0.02"\" fill=\"white\"/>";
        print "</svg>";
      }' > /tmp/eww-clock.svg
      echo "/tmp/eww-clock.svg"
    '';
  };

  xdg.configFile."eww/eww.yuck".text = ''
    (defpoll clock-path :interval "10s" `~/.config/eww/clock.sh`)

    (defwidget clock []
      (image :path clock-path :image-width 320 :image-height 320))

    (defwindow clock
      :monitor 0
      :geometry (geometry
        :x "20px"
        :y "20px"
        :width "320px"
        :height "320px"
        :anchor "top left")
      :stacking "bottom"
      :exclusive false
      (clock))
  '';

  xdg.configFile."eww/eww.scss".text = ''
    * {
      background-color: transparent;
    }
  '';
}
