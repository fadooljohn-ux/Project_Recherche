"""Compare marginal GLS and an independent penalized-noise fit; no period scan."""
import argparse
from pathlib import Path
import numpy as np
from scipy import linalg
import target_calibration as cal


def audit(prepared, output):
    with np.load(prepared/'timing.npz') as z:
        a={k:z[k] for k in z.files}
    reference=np.loadtxt(prepared/'reference.txt',dtype=np.longdouble)
    sigma=np.asarray(reference[:,4]*1e-6,float)
    y=np.asarray(reference[:,3],float)
    design=np.asarray(a['design'],float)
    factors=[np.loadtxt(prepared/('reference.txt.'+name),ndmin=2) for name in ['red','dm']]
    ecorr_path=prepared/'reference.txt.ecorr'
    if ecorr_path.exists() and ecorr_path.stat().st_size:
        e=np.loadtxt(ecorr_path,ndmin=2)
        for anchor in np.unique(e[:,0]):
            r=e[e[:,0]==anchor];column=np.zeros((len(y),1))
            column[r[:,1].astype(int),0]=r[:,2]
            factors.append(column)
    F=np.column_stack(factors)
    C=F@F.T
    C.flat[::len(y)+1]+=sigma**2
    L=linalg.cholesky(C,lower=True)
    yd=linalg.solve_triangular(L,y,lower=True)
    D=linalg.solve_triangular(L,design,lower=True)
    scale=np.linalg.norm(D,axis=0)
    beta,*_=linalg.lstsq(D/scale,yd,cond=1e-12,lapack_driver='gelsd')
    post=yd-D/scale@beta
    marginal=float(post@post)
    # Noise coefficients have unit Gaussian priors because F already includes
    # their physical amplitudes. Timing parameters have no prior penalty.
    W=design/sigma[:,None]
    timing_scale=np.linalg.norm(W,axis=0)
    joint=np.column_stack([W/timing_scale,F/sigma[:,None]])
    prior=np.zeros((F.shape[1],joint.shape[1]))
    prior[:,design.shape[1]:]=np.eye(F.shape[1])
    augmented=np.vstack([joint,prior]);rhs=np.r_[y/sigma,np.zeros(F.shape[1])]
    norms=np.linalg.norm(augmented,axis=0)
    solution,_,rank,_=linalg.lstsq(augmented/norms,rhs,cond=1e-12,lapack_driver='gelsd')
    solution/=norms
    remaining=y/sigma-joint@solution
    data_chi2=float(remaining@remaining)
    prior_chi2=float(np.sum(solution[design.shape[1]:]**2))
    total=data_chi2+prior_chi2
    difference=abs(total-marginal)
    accepted=bool(np.isclose(total,marginal,rtol=1e-7,atol=1e-5) and rank==joint.shape[1])
    record={'status':'LIKELIHOOD_EQUIVALENT' if accepted else 'LIKELIHOOD_MISMATCH',
        'marginal_gls_chi2':marginal,'augmented_data_chi2':data_chi2,
        'noise_prior_penalty':prior_chi2,'augmented_total_chi2':total,
        'absolute_difference':difference,'dof':len(y)-design.shape[1],
        'marginal_reduced_chi2':marginal/(len(y)-design.shape[1]),
        'data_only_reduced_chi2':data_chi2/(len(y)-design.shape[1]),
        'joint_rank':int(rank),'joint_columns':joint.shape[1],
        'weighted_raw_rms_us':float(np.sqrt(np.average((y-np.average(y,weights=1/sigma**2))**2,weights=1/sigma**2))*1e6),
        'white_postfit_rms_us':float(np.sqrt(np.sum(remaining**2)/np.sum(1/sigma**2))*1e6),
        'scope':'No frequency search or noise-amplitude adjustment; fixed released inputs',
        'prepared':str(prepared),'inputs':{p.name:cal.digest(p) for p in [prepared/'timing.npz',prepared/'reference.txt',prepared/'reference.txt.red',prepared/'reference.txt.dm',ecorr_path] if p.exists()},
        'audit_code_sha256':cal.digest(__file__)}
    cal.write(output,record)
    print('LIKELIHOOD_AUDIT',record['status'],difference,flush=True)
    if not accepted:raise ValueError('Independent likelihood formulations disagree')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();audit(args.prepared.resolve(),args.output.resolve())
