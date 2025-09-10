apiVersion: batch/v1
kind: Job
metadata:
  name: pid-sim-validate
  namespace: pid-sim-dev
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: pid-sim
          image: ${IMAGE}         # <- wstawiane w CI
          imagePullPolicy: IfNotPresent
          envFrom:
            - configMapRef:
                name: pid-sim-config
          env:
            - name: OUT_DIR
              value: /out
          volumeMounts:
            - name: outdir
              mountPath: /out
      volumes:
        - name: outdir
          emptyDir: {}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: pid-sim-config
  namespace: pid-sim-dev
data:
  # zamienimy configmap.env na pary key: value podczas renderowania
  # ten blok bedzie nadpisany przez skrypt render.sh
