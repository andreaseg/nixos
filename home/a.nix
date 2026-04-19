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
    hyprpicker
  ];

  home.sessionVariables = {
    TERMINAL = "kitty";
  };

  programs.home-manager.enable = true;
  programs.kitty = {
    enable = true;
    extraConfig = ''
      # Route Nerd Font PUA glyphs to Symbols Nerd Font Mono.
      symbol_map U+E000-U+E0EF,U+E200-U+E2A9,U+E300-U+E3E3,U+E5FA-U+E6B1,U+E700-U+E7C5,U+EA60-U+EBEB,U+ED00-U+EFFF,U+F000-U+F2FF,U+F400-U+F533,U+F0001-U+F1AF0 Symbols Nerd Font Mono
      # Route CJK codepoints to Sarasa Mono J (Iosevka + Source Han Sans JP).
      # Ranges: CJK symbols/hiragana/katakana/unified ideographs (3000-9FFF),
      # CJK compatibility ideographs (F900-FAFF), halfwidth/fullwidth forms
      # (FF00-FFEF), CJK unified ideographs extension B (20000-2A6DF).
      symbol_map U+3000-U+9FFF,U+F900-U+FAFF,U+FF00-U+FFEF,U+20000-U+2A6DF Sarasa Mono J
    '';
    settings = {
      # Kanagawa Wave
      background            = "#1F1F28";
      foreground            = "#DCD7BA";
      selection_background  = "#2D4F67";
      selection_foreground  = "#C8C093";
      url_color             = "#72A7BC";
      cursor                = "#C8C093";
      cursor_text_color     = "#1F1F28";

      font_family = "Fira Code";
      font_size   = "13.0";

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

home.stateVersion = "25.11";
}
