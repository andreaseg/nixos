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

    theme = lib.mkOption {
      type = lib.types.enum [ "dark" "light" ];
      default = "dark";
      description = ''
        Color theme preset. Sets sensible defaults for dark or light
        terminals. Individual color options can still override.
      '';
    };

    colors = {
      title    = strOpt "default";
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
        label   = strOpt "italic dim";
        value   = strOpt "default";
        reading = strOpt "cyan";
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

    wanikani = {
      enable = lib.mkEnableOption "WaniKani integration";
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
    # Theme-sensitive defaults — lower priority than explicit user values,
    # higher priority than the strOpt defaults above.
    programs.jisho.colors.text.reading = lib.mkDefault (
      if cfg.theme == "light" then "blue" else "cyan"
    );
    programs.jisho.colors.text.label = lib.mkDefault (
      if cfg.theme == "light" then "italic" else "italic dim"
    );
    programs.jisho.colors.badge.warning = lib.mkDefault (
      if cfg.theme == "light" then "dark_orange" else "yellow"
    );
    programs.jisho.colors.badge.jlpt = lib.mkDefault (
      if cfg.theme == "light" then "dark_orange" else "yellow"
    );

    home.packages = [
      (pkgs.python3Packages.buildPythonApplication {
        pname = "jisho";
        version = "0.1.0";
        src = ./.;
        pyproject = true;
        build-system = [ pkgs.python3Packages.setuptools ];
        dependencies = with pkgs.python3Packages; [ requests rich ];
        nativeCheckInputs = [ pkgs.python3Packages.pytest ];
        checkPhase = ''
          runHook preCheck
          pytest tests/ -q
          runHook postCheck
        '';
      })
    ];

    xdg.configFile."jisho/config.json".text = builtins.toJSON {
      inherit (cfg) colors badges anki cache format wanikani;
    };
  };
}
