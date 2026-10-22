from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

#Si una config olvida 'permissions' se cae a IsAuthenticated (fail-closed):
#un viewset sin permisos definidos nunca debe quedar abierto por accidente.
DEFAULT_PERMISSIONS   =   [IsAuthenticated]

#================================
# USER VIEWSET
#================================
class UserBaseViewSet(viewsets.GenericViewSet):
    view_config         =   {}

    def get_action_view(self):
        config          =   self.view_config.get(self.action)
        if not config:
            raise ValueError(f'No hay configuración disponible para la acción solicitada: {self.action}')
        return config

    def get_serializer_class(self):
        return self.get_action_view()['serializer']

    def get_queryset(self):
        queryset        =   self.get_action_view()['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset

    def get_permissions(self):
        permissions     =   self.get_action_view().get('permissions', DEFAULT_PERMISSIONS)
        return   [permission() for permission in permissions]


        
    #///RETRIEVE METHOD///
    def retrieve(self, request, *args, **kwargs):
        instance    =   self.get_queryset()
        serializer  =   self.get_serializer(instance)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
    #///UPDATE METHOD///
    def update(self, request, *args, **kwargs):
        message          =  self.get_action_view().get('message', 'Actualizado correctamente')
        instance         =  self.get_queryset()
        serializer       =  self.get_serializer(instance, data=request.data, context={'request': request}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'Exito' :   message
            }, status=status.HTTP_200_OK
        )
    
    #///LIST METHOD///
    def list(self, request, *args, **kwargs):
        queryset        =   self.get_queryset()
        page            =   self.paginate_queryset(queryset)
        if page is not None:
            serializer  =    self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)   
        serializer      =    self.get_serializer(queryset, many=True)
        return Response(serializer.data)

#================================
# USER PASSWORD UPDATE VIEWSET
#================================
class UserPassWordBaseViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin,):
    view_config         =   {}
    def get_serializer_class(self, *args, **kwargs):
        return self.view_config['create']['serializer']
    def get_queryset(self):
        self.queryset   =    self.view_config['create']['queryset']
        if callable(self.queryset):
            return self.queryset(self)
        return self.queryset
    def get_permissions(self):
        permissions     =   self.view_config['create'].get('permissions', DEFAULT_PERMISSIONS)
        return [permission() for permission in permissions]
    #///CREATE METHOD///
    def create(self,request,*args, **kwargs):
        message         =   self.view_config['create']['message']
        instance        =   self.get_queryset()
        serializer      =   self.get_serializer(instance = instance, data = request.data, context = {'request' : request}, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return  Response(
            {
                'Exito' : message 
            }, status = status.HTTP_200_OK
        )

#================================#================================#================================#================================


#================================
# USER PROFILE BASEVIEWSET
#================================
class UserProfileBaseVieSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    view_config         =   {}
    def get_action_view(self):
        config          =   self.view_config.get(self.action)
        if not config:
            raise ValueError('Acción no permitida')
        return config
    def get_serializer_class(self):
        serializer      =   self.get_action_view()['serializer']
        return serializer
    def get_queryset(self):
        queryset        =   self.get_action_view()['queryset']
        if callable(queryset):
            return queryset(self)
        return queryset
    def get_permissions(self):
        permissions     =   self.get_action_view().get('permissions', DEFAULT_PERMISSIONS)
        return [permission() for permission in permissions]

    #/// RETRIEVE METHOD ///
    def retrieve(self, request, *args, **kwargs):
        instance    =   self.get_queryset()
        serializer  =   self.get_serializer(instance)
        return Response(serializer.data, status = status.HTTP_200_OK)

    #///  UPDATE METHOD ///
    def update(self, request, *args, **kwargs):
        message     =   self.get_action_view()['message']
        instance    =   self.get_queryset()
        serializer  =   self.get_serializer(instance = instance, data = request.data, context = {'request':request}, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' :   message
            }, status = status.HTTP_200_OK
        )
#================================#================================#================================#================================

#================================
# REGISTER USER BASE VIEWSET
#================================
class RegisterUserBaseViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    view_config         =   {}
    def get_serializer_class(self, *args, **kwargs):
        return self.view_config['create']['serializer']
    def get_queryset(self):
        self.queryset   =   self.view_config['create']['queryset']
        if callable(self.queryset):
            return self.queryset(self)
        return self.queryset
    def get_permissions(self):
        permissions     =   self.view_config['create'].get('permissions', DEFAULT_PERMISSIONS)
        return [permission() for permission in permissions]

    #/// CREATE METHOD ///
    def create(self,request, *args, **kwargs):
        message     =   self.view_config['create']['message']
        serializer  =   self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(
            {
                'Exito' : message
            }, status = status.HTTP_201_CREATED
        )