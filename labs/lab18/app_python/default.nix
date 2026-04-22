{ pkgs ? import <nixpkgs> {} }:

let
  cleanSrc = pkgs.lib.cleanSourceWith {
    src = ./.;
    filter = path: type:
      let
        name = builtins.baseNameOf path;
      in
        !(
          name == "result" ||
          name == "__pycache__" ||
          pkgs.lib.hasSuffix ".pyc" name
        );
  };

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    fastapi
    prometheus-client
    python-json-logger
    uvicorn
  ]);
in
pkgs.stdenvNoCC.mkDerivation {
  pname = "devops-info-service";
  version = "1.0.0";
  src = cleanSrc;

  dontBuild = true;
  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin" "$out/libexec/devops-info-service"
    cp "$src/app.py" "$out/libexec/devops-info-service/app.py"
    cp "$src/requirements.txt" "$out/libexec/devops-info-service/requirements.txt"

    makeWrapper ${pythonEnv}/bin/python "$out/bin/devops-info-service" \
      --set-default HOST "0.0.0.0" \
      --set-default PORT "5000" \
      --add-flags "$out/libexec/devops-info-service/app.py"

    runHook postInstall
  '';

  meta = with pkgs.lib; {
    description = "Reproducible DevOps Info Service build";
    mainProgram = "devops-info-service";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
