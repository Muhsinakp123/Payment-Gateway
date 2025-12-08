from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Order, Transaction
from .serializers import ProductSerializer, OrderSerializer, TransactionSerializer
from .paypal_config import paypalrestsdk
from django.http import JsonResponse

@api_view(['GET'])
def get_products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_product(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_single_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product)
    return Response(serializer.data)


@api_view(['PUT'])
def update_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
def patch_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    product.delete()
    return Response({"message": "Product deleted"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def get_orders(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_order(request):
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    order = Order(product=product, quantity=quantity)
    order.save()

    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_single_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['PUT'])
def update_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderSerializer(order, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
def patch_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    order.delete()
    return Response({"message": "Product deleted"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def create_payment(request):
    order_id = request.data.get('order_id')

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

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
        # Save transaction in DB
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

    print("PayPal Error:", payment.error)  # Log for debugging
    return Response({"error": payment.error}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def execute_payment(request):
    payment_id = request.GET.get("paymentId")  # from query param
    payer_id = request.GET.get("PayerID")     # from query param

    if not payment_id or not payer_id:
        return Response({"error": "Missing paymentId or PayerID"}, status=400)

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    if payment.execute({"payer_id": payer_id}):
        # Update transaction
        transaction = Transaction.objects.get(payment_id=payment_id)
        transaction.status = payment.state
        transaction.save()

        # Update order
        order = transaction.order
        order.status = "PAID"
        order.save()

        return Response({"status": "Payment Successful"})
    else:
        return Response({"error": payment.error}, status=400)

@api_view(['GET'])
def cancel_payment(request):
    return Response({"status": "Payment cancelled"})

