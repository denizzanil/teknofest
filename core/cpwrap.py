import CoolProp.CoolProp as CP
import traceback

def PropsSI(output, in1, val1, in2, val2, fluid):
    try:
        print(f"CP.PropsSI call: out={output}, {in1}={val1}, {in2}={val2}, fluid={fluid}")
    except Exception:
        pass
    try:
        return CP.PropsSI(output, in1, val1, in2, val2, fluid)
    except Exception as e:
        print(f"CP.PropsSI exception: {e}")
        traceback.print_exc()
        raise
