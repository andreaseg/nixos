{ config, pkgs, ... }:

{
  imports = [
    ./hyprland.nix
    ./eww.nix
    ./shell.nix
    ./jisho
  ];

  home.username = "a";
  home.homeDirectory = "/home/a";

  home.packages = with pkgs; [
    kdePackages.kate
    google-chrome
    mpv
    pavucontrol
    nerd-fonts.symbols-only
    python3
    glow
    gnumake
    bat
  ];

  home.sessionVariables = {
    TERMINAL = "kitty";
  };

  programs.home-manager.enable = true;
  programs.kitty = {
    enable = true;
    settings = {
      # Kanagawa Wave
      background            = "#1F1F28";
      foreground            = "#DCD7BA";
      selection_background  = "#2D4F67";
      selection_foreground  = "#C8C093";
      url_color             = "#72A7BC";
      cursor                = "#C8C093";
      cursor_text_color     = "#1F1F28";

      font_family = "Noto Sans Mono";
      font_size   = "11.0";

      # Black
      color0  = "#090618";
      color8  = "#727169";
      # Red
      color1  = "#C34043";
      color9  = "#E82424";
      # Green
      color2  = "#76946A";
      color10 = "#98BB6C";
      # Yellow
      color3  = "#C0A36E";
      color11 = "#E6C384";
      # Blue
      color4  = "#7E9CD8";
      color12 = "#7FB4CA";
      # Magenta
      color5  = "#957FB8";
      color13 = "#938AA9";
      # Cyan
      color6  = "#6A9589";
      color14 = "#7AA89F";
      # White
      color7  = "#C8C093";
      color15 = "#DCD7BA";
    };
  };
  programs.git.enable = true;
  programs.jisho = {
    enable = true;
    wanikani.enable = true;
    anki.fields = {
      "Migaku Japanese CUSTOM STYLING" = "Target Word Simplified";
    };
    colors = {
      title = "#DCD7BA";        # fujiWhite
      badge = {
        anki     = "bold #98BB6C";  # springGreen
        wanikani = "bold #957FB8";  # oniViolet
        common   = "#76946A";       # autumnGreen
        jlpt     = "#C0A36E";       # boatYellow2
        warning  = "#FFA066";       # surimiOrange
        danger   = "#C34043";       # autumnRed
      };
      border = {
        anki     = "#76946A";   # autumnGreen
        wanikani = "#957FB8";   # oniViolet
        default  = "#7E9CD8";   # crystalBlue
      };
      text = {
        label   = "italic dim";
        value   = "#C8C093";    # oldWhite
        reading = "#6A9589";    # waveAqua1
      };
    };
  };

  # Tell fontconfig that Source Han Mono is monospace (spacing=100).
  # Fontconfig's glyph-width scan classifies CJK dual-width fonts as
  # non-mono; this override ensures Kitty lists and loads the font.
  xdg.configFile."fontconfig/conf.d/50-source-han-mono.conf".text = ''
    <?xml version="1.0"?>
    <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
    <fontconfig>
      <match target="font">
        <test name="family">
          <string>Source Han Mono</string>
        </test>
        <edit name="spacing" mode="assign" binding="strong">
          <int>100</int>
        </edit>
      </match>
    </fontconfig>
  '';

  home.stateVersion = "25.11";
}
