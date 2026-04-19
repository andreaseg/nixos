{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    grim                  # Screenshot tool
    slurp                 # Region selector
    wl-clipboard          # Clipboard utilities
    mako                  # Notification daemon
    networkmanagerapplet  # WiFi/network tray applet
    hyprpaper             # Wallpaper daemon
  ];

  wayland.windowManager.hyprland = {
    enable = true;
    settings = {
      "$mod" = "SUPER";
      "$terminal" = "kitty";
      "$menu" = "wofi --show drun";

      monitor = ",preferred,auto,1";

      # NVIDIA-specific environment variables
      env = [
        "LIBVA_DRIVER_NAME,nvidia"
        "XDG_SESSION_TYPE,wayland"
        "GBM_BACKEND,nvidia-drm"
        "__GLX_VENDOR_LIBRARY_NAME,nvidia"
        "NVD_BACKEND,direct"
        "ELECTRON_OZONE_PLATFORM_HINT,auto"
        # Fcitx5 input method — GTK_IM_MODULE explicitly cleared because fcitx5 sets it
        # via profile.d, but GTK4 uses the Wayland input protocol directly
        "GTK_IM_MODULE,"
        "QT_IM_MODULE,fcitx"
        "XMODIFIERS,@im=fcitx"
        "SDL_IM_MODULE,fcitx"
      ];

      cursor = {
        no_hardware_cursors = true;
      };

      general = {
        gaps_in = 5;
        gaps_out = 10;
        border_size = 2;
        "col.active_border" = "rgba(5D767Dee) rgba(E58950ee) 45deg";
        "col.inactive_border" = "rgba(5D767D66)";
        layout = "dwindle";
      };

      decoration = {
        rounding = 10;
        blur = {
          enabled = true;
          size = 3;
          passes = 1;
        };
        shadow = {
          enabled = true;
          range = 4;
          render_power = 3;
        };
      };

      animations = {
        enabled = true;
        bezier = "myBezier, 0.05, 0.9, 0.1, 1.05";
        animation = [
          "windows, 1, 7, myBezier"
          "windowsOut, 1, 7, default, popin 80%"
          "border, 1, 10, default"
          "fade, 1, 7, default"
          "workspaces, 1, 6, default"
        ];
      };

      dwindle = {
        pseudotile = true;
        preserve_split = true;
      };

      input = {
        kb_layout = "no";
        kb_variant = "winkeys";
        follow_mouse = 1;
        touchpad = {
          natural_scroll = true;
        };
      };

      # Autostart
      exec-once = [
        "hyprpaper"
        "waybar"
        "mako"
        "nm-applet --indicator"
        "eww open clock"
        "fcitx5 -d"
      ];

      # Keybindings
      bind = [
        "$mod, Return, exec, $terminal"
        "$mod, Q, killactive"
        "$mod, M, exit"
        "$mod, E, exec, thunar"
        "$mod, V, togglefloating"
        "$mod, D, exec, $menu"
        "$mod, P, pseudo"
        "$mod, J, togglesplit"
        "$mod, F, fullscreen"

        # Move focus
        "$mod, left, movefocus, l"
        "$mod, right, movefocus, r"
        "$mod, up, movefocus, u"
        "$mod, down, movefocus, d"
        "$mod, H, movefocus, l"
        "$mod, L, movefocus, r"
        "$mod, K, movefocus, u"
        "$mod, J, movefocus, d"

        # Switch workspaces
        "$mod, 1, workspace, 1"
        "$mod, 2, workspace, 2"
        "$mod, 3, workspace, 3"
        "$mod, 4, workspace, 4"
        "$mod, 5, workspace, 5"
        "$mod, 6, workspace, 6"
        "$mod, 7, workspace, 7"
        "$mod, 8, workspace, 8"
        "$mod, 9, workspace, 9"
        "$mod, 0, workspace, 10"

        # Move active window to workspace
        "$mod SHIFT, 1, movetoworkspace, 1"
        "$mod SHIFT, 2, movetoworkspace, 2"
        "$mod SHIFT, 3, movetoworkspace, 3"
        "$mod SHIFT, 4, movetoworkspace, 4"
        "$mod SHIFT, 5, movetoworkspace, 5"
        "$mod SHIFT, 6, movetoworkspace, 6"
        "$mod SHIFT, 7, movetoworkspace, 7"
        "$mod SHIFT, 8, movetoworkspace, 8"
        "$mod SHIFT, 9, movetoworkspace, 9"
        "$mod SHIFT, 0, movetoworkspace, 10"

        # Scroll through workspaces
        "$mod, mouse_down, workspace, e+1"
        "$mod, mouse_up, workspace, e-1"

        # Screenshot
        ", Print, exec, grim -g \"$(slurp)\" - | wl-copy"
        "SHIFT, Print, exec, grim - | wl-copy"
      ];

      # Mouse bindings
      bindm = [
        "$mod, mouse:272, movewindow"
        "$mod, mouse:273, resizewindow"
      ];
    };
  };

  programs.waybar = {
    enable = true;
    settings = {
      mainBar = {
        layer = "top";
        position = "top";
        height = 30;
        modules-left = [ "hyprland/workspaces" ];
        modules-center = [ "hyprland/window" ];
        # network is intentionally omitted — handled by nm-applet in tray
        # IME state is shown via the fcitx5 tray icon
        modules-right = [ "pulseaudio" "battery" "tray" "clock"];

        clock = {
          format = "{:%H:%M}";
        };

        pulseaudio = {
          format = "{icon}";
          format-muted = "󰝟";
          format-icons = {
            default = [ "󰕿" "󰖀" "󰕾" ];
          };
          on-click = "pavucontrol";
        };

        battery = {
          format = "{icon}";
          format-icons = [ "󰁺" "󰁻" "󰁼" "󰁽" "󰁾" "󰁿" "󰂀" "󰂁" "󰂂" "󰁹" ];
        };

        tray = {
          spacing = 10;
        };
      };
    };
    style = ''
      * {
        font-family: "Fira Code", "Symbols Nerd Font", sans-serif;
        font-size: 13px;
      }

      window#waybar {
        background-color: rgba(31, 31, 40, 0.92); /* sumiInk1 */
        color: #DCD7BA;                            /* fujiWhite */
      }

      #workspaces button {
        padding: 0 5px;
        color: #727169; /* fujiGray */
      }

      #workspaces button.active {
        color: #DCD7BA;
        background-color: #2D4F67; /* waveBlue2 */
        border-radius: 4px;
      }

      #workspaces button:hover {
        background-color: #223249; /* waveBlue1 */
        border-radius: 4px;
      }

      #clock {
        color: #7E9CD8; /* crystalBlue */
        padding: 0 10px;
      }

      #battery {
        color: #DCD7BA; /* fujiWhite */
        padding: 0 10px;
      }

      #pulseaudio {
        color: #DCD7BA; /* fujiWhite */
        padding: 0 10px;
      }

      #tray {
        padding: 0 10px;
      }

      #tray > widget {
        -gtk-icon-style: symbolic;
        color: #DCD7BA; /* fujiWhite */
      }
    '';
  };

  programs.wofi = {
    enable = true;
    settings = {
      width = 500;
      height = 300;
      show = "drun";
      prompt = "Search...";
      allow_images = true;
    };
    style = ''
      window {
        background-color: rgba(31, 31, 40, 0.97); /* sumiInk1 */
        border-radius: 10px;
      }

      #input {
        margin: 10px;
        border: none;
        border-radius: 5px;
        background-color: #2A2A37; /* sumiInk2 */
        color: #DCD7BA;            /* fujiWhite */
      }

      #entry {
        padding: 10px;
        color: #C8C093; /* oldWhite */
      }

      #entry:selected {
        background-color: #2D4F67; /* waveBlue2 */
        color: #DCD7BA;
      }
    '';
  };

  xdg.configFile."hypr/hyprpaper.conf".text = ''
    preload = /home/a/Wallpapers/wallhaven-d8e373.jpg
    wallpaper = eDP-1,/home/a/Wallpapers/wallhaven-d8e373.jpg
  '';

  services.mako = {
    enable = true;
    settings = {
      default-timeout = 5000;
      border-radius = 5;
      background-color = "#1F1F28"; /* sumiInk1 */
      text-color = "#DCD7BA";      /* fujiWhite */
      border-color = "#7E9CD8";    /* crystalBlue */
    };
  };
}
