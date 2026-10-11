open Trade_engine

let money = Alcotest.testable Money.pp Money.equal

let overflow =
  Alcotest.of_pp (fun fmt `Overflow -> Format.pp_print_string fmt "`Overflow")

let mul_qty_result = Alcotest.result money overflow

(* Whole shares expressed in micro-shares. *)
let shares n = Int64.mul n Money.micro_per_share
let usd d = Money.of_cents (d * 100)

let micro_round_trip () =
  List.iter
    (fun n ->
      Alcotest.(check int64)
        (Printf.sprintf "of_micro/to_micro %Ld" n)
        n
        Money.(to_micro (of_micro n)))
    [ 0L; 1L; -1L; 123_456_789L; Int64.max_int; Int64.min_int ]

let of_cents_scales () =
  Alcotest.(check int64)
    "12345 cents" 123_450_000L
    Money.(to_micro (of_cents 12345));
  Alcotest.(check int64) "-1 cent" (-10_000L) Money.(to_micro (of_cents (-1)));
  Alcotest.check money "zero" Money.zero (Money.of_cents 0)

let to_string_format () =
  List.iter
    (fun (n, expected) ->
      Alcotest.(check string)
        expected expected
        (Money.to_string (Money.of_micro n)))
    [
      (0L, "0.000000");
      (1L, "0.000001");
      (-1L, "-0.000001");
      (123_450_000L, "123.450000");
      (-1_000_000L, "-1.000000");
      (Int64.max_int, "9223372036854.775807");
      (Int64.min_int, "-9223372036854.775808");
    ]

let add_sub_identity () =
  let a = Money.of_cents 100_000 and b = Money.of_cents (-250) in
  Alcotest.check money "a + b - b = a" a Money.(sub (add a b) b);
  Alcotest.check money "a - a = 0" Money.zero (Money.sub a a);
  Alcotest.check money "a + 0 = a" a (Money.add a Money.zero);
  Alcotest.check money "a + (-a) = 0" Money.zero Money.(add a (neg a));
  Alcotest.check money "neg (neg a) = a" a Money.(neg (neg a));
  Alcotest.check money "a + b = b + a" (Money.add a b) (Money.add b a)

let add_sub_overflow () =
  let max = Money.of_micro Int64.max_int
  and min = Money.of_micro Int64.min_int in
  let one = Money.of_micro 1L in
  let raises name f =
    Alcotest.check_raises name Money.Overflow (fun () -> ignore (f ()))
  in
  raises "max + 1" (fun () -> Money.add max one);
  raises "min - 1" (fun () -> Money.sub min one);
  raises "neg min" (fun () -> Money.neg min);
  raises "0 - min" (fun () -> Money.sub Money.zero min);
  raises "of_cents overflow" (fun () -> Money.of_cents max_int);
  Alcotest.check money "max + min = -1" (Money.of_micro (-1L))
    (Money.add max min);
  Alcotest.check money "-1 - min = max" max
    (Money.sub (Money.of_micro (-1L)) min);
  Alcotest.check money "neg max"
    (Money.of_micro (Int64.succ Int64.min_int))
    (Money.neg max)

let mul_qty_scaling () =
  let check name expected price qty =
    Alcotest.check mul_qty_result name expected
      (Money.mul_qty price ~qty_micro:qty)
  in
  check "$100 x 10 shares" (Ok (usd 1000)) (usd 100) (shares 10L);
  check "$100 x 0.5 share" (Ok (usd 50)) (usd 100) 500_000L;
  check "$1.50 x 2.5 shares"
    (Ok (Money.of_cents 375))
    (Money.of_cents 150) 2_500_000L;
  check "$0.000001 x 0.5 share truncates to 0" (Ok Money.zero)
    (Money.of_micro 1L) 500_000L;
  check "$0.000003 x 0.5 share truncates to 0.000001"
    (Ok (Money.of_micro 1L))
    (Money.of_micro 3L) 500_000L;
  check "$5000 x 10000 shares (naive product overflows int64)"
    (Ok (usd 50_000_000))
    (usd 5000) (shares 10_000L);
  check "max price x 1 share"
    (Ok (Money.of_micro Int64.max_int))
    (Money.of_micro Int64.max_int)
    (shares 1L);
  check "zero qty" (Ok Money.zero) (usd 100) 0L;
  check "zero price" (Ok Money.zero) Money.zero (shares 10L)

let mul_qty_sign_symmetry () =
  let p = Money.of_cents 12_345 and q = 1_234_567L in
  let value price qty =
    match Money.mul_qty price ~qty_micro:qty with
    | Ok v -> v
    | Error `Overflow -> Alcotest.fail "unexpected overflow"
  in
  let buy = value p q and sell = value p (Int64.neg q) in
  Alcotest.check money "sell = neg buy" (Money.neg buy) sell;
  Alcotest.check money "buy + sell = 0" Money.zero (Money.add buy sell);
  Alcotest.check money "neg price x neg qty = buy" buy
    (value (Money.neg p) (Int64.neg q));
  Alcotest.check money "neg price x qty = sell" sell (value (Money.neg p) q)

let mul_qty_overflow () =
  let check name expected price qty =
    Alcotest.check mul_qty_result name expected
      (Money.mul_qty price ~qty_micro:qty)
  in
  check "max x 2 shares" (Error `Overflow)
    (Money.of_micro Int64.max_int)
    (shares 2L);
  check "max x 1.000001 shares" (Error `Overflow)
    (Money.of_micro Int64.max_int)
    (Int64.succ (shares 1L));
  check "min price" (Error `Overflow) (Money.of_micro Int64.min_int) 1L;
  check "min qty" (Error `Overflow) (usd 1) Int64.min_int

let compare_orders () =
  let a = Money.of_cents 1 and b = Money.of_cents 2 in
  Alcotest.(check bool) "a < b" true (Money.compare a b < 0);
  Alcotest.(check bool) "b > a" true (Money.compare b a > 0);
  Alcotest.(check int) "a = a" 0 (Money.compare a a);
  Alcotest.(check bool) "neg a < a" true (Money.compare (Money.neg a) a < 0);
  Alcotest.(check bool) "equal" true (Money.equal a (Money.of_micro 10_000L));
  Alcotest.(check bool) "not equal" false (Money.equal a b)

let tests =
  [
    Alcotest.test_case "micro round-trip" `Quick micro_round_trip;
    Alcotest.test_case "of_cents scales by 10_000" `Quick of_cents_scales;
    Alcotest.test_case "to_string format" `Quick to_string_format;
    Alcotest.test_case "add/sub identities" `Quick add_sub_identity;
    Alcotest.test_case "add/sub/neg overflow" `Quick add_sub_overflow;
    Alcotest.test_case "mul_qty scaling" `Quick mul_qty_scaling;
    Alcotest.test_case "mul_qty sign symmetry" `Quick mul_qty_sign_symmetry;
    Alcotest.test_case "mul_qty overflow" `Quick mul_qty_overflow;
    Alcotest.test_case "compare/equal" `Quick compare_orders;
  ]
