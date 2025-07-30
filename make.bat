:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: LICENSING                                                                    :
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::
:: Copyright 2020 Esri
::
:: Licensed under the Apache License, Version 2.0 (the "License"); You
:: may not use this file except in compliance with the License. You may
:: obtain a copy of the License at
::
:: http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing, software
:: distributed under the License is distributed on an "AS IS" BASIS,
:: WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
:: implied. See the License for the specific language governing
:: permissions and limitations under the License.
::
:: A copy of the license is available in the repository's
:: LICENSE file.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: VARIABLES                                                                    :
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

SETLOCAL
SET PROJECT_DIR=%cd%
::SET SCRIPTS_DIR=%~dp0\scripts
SET PROJECT_NAME=PROJECT_AMATS_CAP
SET SUPPORT_LIBRARY=amats_cap
SET ENV_NAME=amats_cap

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: COMMANDS                                                                     :
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Jump to command
GOTO %1

:: Perform user variable setup
:::setup_user
::    ENDLOCAL & (
::        ECHO ^>^>^> running user_setup.py
::        CALL activate "%ENV_NAME%"
::        CALL python "%SCRIPTS_DIR%"\setup_user.py
::        ECHO ^>^>^> User setup complete
::    )
::    EXIT /B

:: Build the local environment from the environment file
::env
::    ENDLOCAL & (
::        :: Install yaml libs to properly read the various ENV files
::        CALL conda install -c conda-forge yaml pyyaml -y
::        :: update environment with package dependencies
::        CALL python check_package_deps.py
::        :: Create new environment from environment file
::       CALL conda env create -f build_environment.yml -y
::        :: Activate the environment so you can get to work
::        CALL conda activate %ENV_NAME%
::        :: Install the local package in development (experimental) mode
::        CALL python -m pip install -e .
::    )
::    EXIT /B

:: Build the local environment from the environment file
:env
    ENDLOCAL & (
        :: Install yaml libs to properly read the various ENV files
        CALL conda install -c conda-forge yaml pyyaml -y
        IF ERRORLEVEL 1 (
            ECHO Error installing yaml libs. Exiting...
            EXIT /B 1
        )

        :: update environment with package dependencies
        CALL python check_package_deps.py
        IF ERRORLEVEL 1 (
            ECHO Error running check_package_deps.py. Exiting...
            EXIT /B 1
        )
        :: check for build_environment.yml before proceeding
        IF NOT EXIST build_environment.yml (
            ECHO check_package_deps.py failed to create build_environment.yml. Exiting...
            EXIT /B 1
        )

        :: Create new environment from environment file
        CALL conda env create -f build_environment.yml -y
        IF ERRORLEVEL 1 (
            ECHO Error creating conda environment. Exiting...
            EXIT /B 1
        )

        :: Activate the environment so you can get to work
        CALL conda activate %ENV_NAME%
        IF ERRORLEVEL 1 (
            ECHO Error activating conda environment. Exiting...
            EXIT /B 1
        )

        :: Install the local package in development (experimental) mode
        CALL python -m pip install -e .
        IF ERRORLEVEL 1 (
            ECHO Error installing local package. Exiting...
            EXIT /B 1
        )
    )
    EXIT /B 0 :: Exit with success code if no errors occurred

:: Build the environment from the arc environment file
:env_arc
    ENDLOCAL & (
        :: Install MAMBA for faster solves
        CALL conda install -c conda-forge mamba yaml -y
        :: Create new environment from environment file
        CALL mamba env create -f environment_arc.yml
        :: Install the local package in development (experimental) mode
        CALL python -m pip install -e .
        :: Activate teh environment so you can get to work
        CALL activate %ENV_NAME_ARC%
    )
    EXIT /B

:: switch local packages to project branch
:switch_branches
    ENDLOCAL & (
        :: Switch local packages to project branch
        CALL python %SCRIPTS_DIR%\package_switcher.py
    )
    EXIT /B

:: Activate the environment
:env_activate
    ENDLOCAL & CALL activate %ENV_NAME%
    EXIT /B

:: Activate the environment
:env_activate_arc
    ENDLOCAL & CALL activate %ENV_NAME_ARC%
    EXIT /B

:: Remove the environment
::env_remove
::	ENDLOCAL & (
::		CALL conda deactivate
::		CALL conda env remove --name %ENV_NAME% -y
::	)
::	EXIT /B

:: Remove the environment
:env_remove
    ENDLOCAL & (
        FOR /F "tokens=*" %%i IN ('conda env list ^| findstr *%ENV_NAME%') DO (
            IF "%%i" NEQ "" (
                CALL conda deactivate
            ) ELSE (
                ECHO Environment %ENV_NAME% is not currently active.
            )
        )
        CALL conda env remove --name %ENV_NAME% -y
    )
    EXIT /B

:: Remove the environment
:env_remove_arc
	ENDLOCAL & (
		CALL conda deactivate
		CALL conda env remove --name %ENV_NAME_ARC% -y
	)
	EXIT /B