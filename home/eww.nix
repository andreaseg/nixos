{ pkgs, ... }:

{
  home.packages = [ pkgs.eww ];

  xdg.configFile."eww/eww.yuck".text = ''
    (defpoll hours   :interval "1s" `date +%H`)
    (defpoll minutes :interval "1s" `date +%M`)
    (defpoll seconds :interval "1s" `date +%S`)

    (defwidget clock []
      (overlay
        (box :class "clock-face")
        (box :class "hand hour-hand"
             :style "transform: rotate(''${(hours % 12) * 30 + minutes * 0.5}deg);")
        (box :class "hand minute-hand"
             :style "transform: rotate(''${minutes * 6}deg);")
        (box :class "hand second-hand"
             :style "transform: rotate(''${seconds * 6}deg);")))

    (defwindow clock
      :monitor 0
      :geometry (geometry
        :x "20px"
        :y "20px"
        :width "150px"
        :height "150px"
        :anchor "top right")
      :stacking "bottom"
      :exclusive false
      (clock))
  '';

  xdg.configFile."eww/eww.scss".text = ''
    .clock-face {
      min-width: 150px;
      min-height: 150px;
      border-radius: 50%;
      background: rgba(30, 30, 46, 0.85);
      border: 2px solid rgba(255, 255, 255, 0.2);
    }

    .hand {
      border-radius: 4px;
      margin: auto;
    }

    .hour-hand {
      min-width: 4px;
      min-height: 40px;
      background: #ffffff;
      transform-origin: bottom center;
    }

    .minute-hand {
      min-width: 3px;
      min-height: 55px;
      background: #cdd6f4;
      transform-origin: bottom center;
    }

    .second-hand {
      min-width: 2px;
      min-height: 65px;
      background: #f38ba8;
      transform-origin: bottom center;
    }
  '';
}
