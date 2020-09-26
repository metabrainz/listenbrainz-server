import * as React from "react";
import { loadStripe } from "@stripe/stripe-js";

//  TODO: move this to the main page
const stripePromise = loadStripe(
  "pk_test_51HVZjjGxs0wjqGlCcH47BUqVtlAZm8qnRZgGS6PhtglPGv3VhSfXOPhuIBbTfFCsPQmus27PnRiT1Oyur47vursm00scSbCsMM"
);

const handlePaymentButtonClick = async (
  timeRange: PatronTimeRange,
  amount: number,
  event: any
) => {
  // Get Stripe.js instance
  const stripe = await stripePromise;
  if (stripe === null) {
    return;
  }

  const response = await fetch(
    `/create-checkout-session?time_range=${timeRange}&amount=${amount}`,
    {
      method: "POST",
    }
  );

  const session = await response.json();

  // When the customer clicks on the button, redirect them to Checkout.
  const result = await stripe.redirectToCheckout({
    sessionId: session.id,
  });

  if (result.error) {
    // If `redirectToCheckout` fails due to a browser or network
    // error, display the localized error message to your customer
    // using `result.error.message`.
  }
};

const PaymentButton = ({
  amount,
  timeRange,
}: {
  amount: number;
  timeRange: PatronTimeRange;
}) => {
  return (
    <div
      className="btn btn-lg btn-info"
      onClick={(event: any) =>
        handlePaymentButtonClick(timeRange, amount, event)
      }
    >
      ${amount}
    </div>
  );
};

export default PaymentButton;
