{ config, pkgs, lib, ... }:

let
  cfg = config.programs.jisho;
  colorOpt = default: lib.mkOption {
    type = lib.types.str;
    inherit default;
  };
in
{
  options.programs.jisho = {
    enable = lib.mkEnableOption "jisho Japanese dictionary CLI";

    colors = {
      title   = colorOpt "bold cyan";
      badge = {
        anki    = colorOpt "bold green";
        wanikani = colorOpt "bold magenta";
        common  = colorOpt "green";
        jlpt    = colorOpt "yellow";
        warning = colorOpt "yellow";
        danger  = colorOpt "red";
      };
      border = {
        anki     = colorOpt "green";
        wanikani = colorOpt "magenta";
        default  = colorOpt "blue";
      };
      text = {
        label = colorOpt "italic dim";
        value = colorOpt "white";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [
      (pkgs.writers.writePython3Bin "jisho"
        { libraries = with pkgs.python3Packages; [ requests rich ]; }
        (builtins.readFile ./jisho.py)
      )
    ];

    xdg.configFile."jisho/colors.json".text =
      builtins.toJSON cfg.colors;
  };
}
