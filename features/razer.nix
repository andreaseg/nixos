{ config, pkgs, ... }:

{
  hardware.openrazer = {
    enable = true;
    users = [ "a" ];
  };

  users.users.a.extraGroups = [ "openrazer" "plugdev" ];

  environment.systemPackages = with pkgs; [
    openrazer-daemon
    polychromatic
  ];
}
