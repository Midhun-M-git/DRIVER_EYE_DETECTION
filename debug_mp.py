try:
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
    print("SUCCESS: mediapipe.python.solutions.face_mesh imported")
    print(f"FaceMesh: {mp_face_mesh.FaceMesh}")
except Exception as e:
    print(f"FAILED: {e}")
    import mediapipe as mp
    print(f"MP dir: {dir(mp)}")
