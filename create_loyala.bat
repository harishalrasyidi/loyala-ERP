@echo off
REM Buat folder dasar dan turunannya
mkdir custom_modules\loyala_project
pushd custom_modules\loyala_project
  mkdir models views data

REM Buat file kosong
type nul > __init__.py
type nul > __manifest__.py
type nul > models\__init__.py
type nul > models\project_request.py
type nul > views\project_request_views.xml
type nul > data\mail_template_feasibility.xml
popd
echo Struktur module loyala_project berhasil dibuat!