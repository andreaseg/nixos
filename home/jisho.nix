{ config, pkgs, lib, ... }:

let
  cfg = config.programs.jisho;
  strOpt = default: lib.mkOption {
    type = lib.types.str;
    inherit default;
  };
in
{
  options.programs.jisho = {
    enable = lib.mkEnableOption "jisho Japanese dictionary CLI";

    colors = {
      title    = strOpt "bold cyan";
      badge = {
        anki     = strOpt "bold green";
        wanikani = strOpt "bold magenta";
        common   = strOpt "green";
        jlpt     = strOpt "yellow";
        warning  = strOpt "yellow";
        danger   = strOpt "red";
      };
      border = {
        anki     = strOpt "green";
        wanikani = strOpt "magenta";
        default  = strOpt "blue";
      };
      text = {
        label = strOpt "italic dim";
        value = strOpt "white";
      };
    };

    badges = {
      anki       = strOpt "★ Anki";
      wkPrefix   = strOpt "⬡ WaniKani L";
      burned     = strOpt " 🔥";
      common     = strOpt "● common";
      jlptPrefix = strOpt "● ";
      notInWk    = strOpt "⚠ not in WaniKani";
      notJouyou  = strOpt "⚠ not jouyou";
    };

    anki = {
      fields = lib.mkOption {
        type = lib.types.attrsOf lib.types.str;
        default = {};
        description = ''
          Map of Anki note type names to the field containing the
          vocabulary word. Add entries for additional note types.
        '';
      };
    };

    format = lib.mkOption {
      type = lib.types.enum [ "rich" "compact" "json" ];
      default = "rich";
      description = ''
        Default output format. Can be overridden per invocation with
        --format. "rich" renders panels, "compact" is one line per
        result, "json" outputs raw JSON.
      '';
    };

    cache = {
      wkTtl = lib.mkOption {
        type = lib.types.int;
        default = 604800;
        description = ''
          WaniKani cache TTL in seconds. The cache is refreshed when
          older than this value. Default: 604800 (7 days).
        '';
      };
      ankiStaleTtl = lib.mkOption {
        type = lib.types.int;
        default = 604800;
        description = ''
          Anki cache age in seconds at which a stale warning is shown.
          Default: 604800 (7 days).
        '';
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

    xdg.configFile."jisho/config.json".text = builtins.toJSON {
      inherit (cfg) colors badges anki cache format;
    };
  };
}
