from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from eventos.models_chat import ChatHistory

class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chat, _ = ChatHistory.objects.get_or_create(user=request.user)
        return Response({"history": chat.history})

    def post(self, request):
        history = request.data.get("history", [])
        chat, _ = ChatHistory.objects.get_or_create(user=request.user)
        chat.history = history
        chat.save()
        return Response({"success": True})

    def delete(self, request):
        chat, _ = ChatHistory.objects.get_or_create(user=request.user)
        chat.history = []
        chat.save()
        return Response({"success": True})
