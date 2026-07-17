from django.shortcuts import render, redirect
from django.contrib import messages
from apps.usuario.decorators import solo_admin
from .models import Empresa
from django.core.exceptions import ValidationError
from django.http import JsonResponse

@solo_admin
def index(request):
    empresa = Empresa.objects.first()
    return render(request, 'empresa/index.html', {'empresa': empresa})

@solo_admin
def crearEmpresa(request):
    if Empresa.objects.exists():
        messages.warning(request, "Ya existe una empresa registrada. Puede editar la información existente.")
        return redirect('empresa:index')

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        nombre = request.POST.get('nombre')
        nit = request.POST.get('nit')
        direccion = request.POST.get('direccion')
        telefono = request.POST.get('telefono')
        email = request.POST.get('email')
        logo = request.FILES.get('logo')
        ciudad = request.POST.get('ciudad', 'La Paz')
        
        latitud = request.POST.get('latitud')
        longitud = request.POST.get('longitud')
        google_maps_link = request.POST.get('google_maps_link')

        latitud = latitud.strip() if latitud and latitud.strip() else None
        longitud = longitud.strip() if longitud and longitud.strip() else None
        google_maps_link = google_maps_link.strip() if google_maps_link else None

        empresa = Empresa(
            nombre=nombre,
            nit=nit,
            direccion=direccion,
            telefono=telefono,
            email=email,
            logo=logo,
            ciudad=ciudad,
            latitud=latitud,
            longitud=longitud,
            google_maps_link=google_maps_link
        )

        try:
            empresa.full_clean()
            empresa.save()
            msg = "Empresa registrada exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
            return redirect('empresa:index')
        except ValidationError as e:
            errors_list = []
            for field, errors in e.message_dict.items():
                for error in errors:
                    errors_list.append(error)
            msg = ", ".join(errors_list)
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
                
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{error}")
            return render(request, 'empresa/crear.html', {
                'datos': request.POST,
                'ciudad_defecto': ciudad
            })

    return render(request, 'empresa/crear.html', {'ciudad_defecto': 'La Paz'})

@solo_admin
def editarEmpresa(request, id_empresa):
    empresa = Empresa.objects.get(id_empresa=id_empresa)

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        empresa.nombre = request.POST.get('nombre')
        empresa.nit = request.POST.get('nit')
        empresa.direccion = request.POST.get('direccion')
        empresa.telefono = request.POST.get('telefono')
        empresa.email = request.POST.get('email')
        empresa.ciudad = request.POST.get('ciudad')
        
        latitud = request.POST.get('latitud')
        longitud = request.POST.get('longitud')
        google_maps_link = request.POST.get('google_maps_link')

        empresa.latitud = latitud.strip() if latitud and latitud.strip() else None
        empresa.longitud = longitud.strip() if longitud and longitud.strip() else None
        empresa.google_maps_link = google_maps_link.strip() if google_maps_link else None

        if request.FILES.get('logo'):
            empresa.logo = request.FILES.get('logo')

        try:
            empresa.full_clean()
            empresa.save()
            msg = "Información de la empresa actualizada exitosamente."
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        except ValidationError as e:
            errors_list = []
            for field, errors in e.message_dict.items():
                for error in errors:
                    errors_list.append(error)
            msg = ", ".join(errors_list)
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)

            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{error}")
        return redirect('empresa:index')

    return redirect('empresa:index')

@solo_admin
def guardarCoordenadas(request, id_empresa):
    if request.method == 'POST':
        try:
            empresa = Empresa.objects.get(id_empresa=id_empresa)
            latitud = request.POST.get('latitud')
            longitud = request.POST.get('longitud')
            
            empresa.latitud = latitud.strip() if latitud and latitud.strip() else None
            empresa.longitud = longitud.strip() if longitud and longitud.strip() else None
            
            empresa.full_clean(exclude=['nombre', 'nit', 'direccion', 'telefono', 'email', 'ciudad'])
            empresa.save()
            return JsonResponse({'success': True, 'message': 'Ubicación guardada automáticamente.'})
        except Empresa.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Empresa no encontrada.'}, status=404)
        except ValidationError as e:
            errors_list = []
            for field, errors in e.message_dict.items():
                for error in errors:
                    errors_list.append(error)
            msg = ", ".join(errors_list)
            return JsonResponse({'success': False, 'message': msg}, status=400)
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
