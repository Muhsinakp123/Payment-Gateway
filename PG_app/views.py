from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from django.contrib.auth.models import User

from .models import Product, Order, Transaction
from .serializers import ProductSerializer, OrderSerializer, TransactionSerializer
from .paypal_config import paypalrestsdk


# ---------------------------
# USER REGISTRATION
# ---------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)

    user = User.objects.create_user(username=username, password=password)
    return Response({"message": "User created successfully"}, status=201)


# ---------------------------
# PRODUCTS (Admin Only for Create/Update/Delete)
# ---------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def get_products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])   # Only Admins
def create_product(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_single_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)

    serializer = ProductSerializer(product)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])  # Only Admins
def update_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)

    serializer = ProductSerializer(product, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])  # Only Admins
def patch_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)

    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])  # Only Admins
def delete_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)

    product.delete()
    return Response({"message": "Product deleted"}, status=204)


# ---------------------------
# ORDERS (Only Logged Users)
# ---------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders(request):
    orders = Order.objects.filter(user=request.user)  # User sees only own orders
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)

    order = Order.objects.create(
        product=product,
        quantity=quantity,
        user=request.user   # Attach logged user
    )

    return Response(OrderSerializer(order).data, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_single_order(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_order(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    serializer = OrderSerializer(order, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def patch_order(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    serializer = OrderSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_order(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    order.delete()
    return Response({"message": "Order deleted"}, status=204)


# ---------------------------
# PAYPAL PAYMENT (Logged Users)
# ---------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request):
    order_id = request.data.get('order_id')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "transactions": [{
            "amount": {"total": f"{order.total_price:.2f}", "currency": order.currency},
            "description": f"Payment for Order {order.id}"
        }],
        "redirect_urls": {
            "return_url": "http://localhost:8000/api/payments/execute/",
            "cancel_url": "http://localhost:8000/api/payments/cancel/"
        }
    })

    if payment.create():
        # save transaction
        Transaction.objects.create(
            order=order,
            payment_id=payment.id,
            amount=order.total_price,
            status=payment.state
        )

        approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)

        return Response({
            "paymentID": payment.id,
            "approval_url": approval_url
        })

    return Response({"error": payment.error}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def execute_payment(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return Response({"error": "Missing paymentId or PayerID"}, status=400)

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    if payment.execute({"payer_id": payer_id}):
        transaction = Transaction.objects.get(payment_id=payment_id)
        transaction.status = payment.state
        transaction.save()

        order = transaction.order
        order.status = "PAID"
        order.save()

        return Response({"status": "Payment Successful"})

    return Response({"error": payment.error}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cancel_payment(request):
    return Response({"status": "Payment cancelled"})
