{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

    home-manager = {
      url = "github:nix-community/home-manager/release-25.11";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }@inputs:
  let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  in
  {
    devShells.x86_64-linux.default = pkgs.mkShell {
      packages = [
        (pkgs.python3.withPackages (ps: with ps; [
          requests rich pytest
        ]))
      ];
    };

    checks.x86_64-linux.jisho = pkgs.runCommand "jisho-tests" {
      nativeBuildInputs = [
        (pkgs.python3.withPackages (ps: with ps; [
          requests rich pytest
        ]))
      ];
    } ''
      cp ${./home/jisho/jisho.py} ./jisho.py
      cp ${./home/jisho/test_jisho.py} ./test_jisho.py
      python -m pytest ./test_jisho.py -v
      touch $out
    '';

    nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit inputs; };
      modules = [
        ./hosts/nixos
        home-manager.nixosModules.home-manager
        {
          home-manager.useGlobalPkgs = true;
          home-manager.useUserPackages = true;
          home-manager.users.a = import ./home/a.nix;
        }
      ];
    };
  };
}
